from __future__ import absolute_import, print_function, division
import ufl

from firedrake import expression
from firedrake import functionspace
from firedrake import functionspaceimpl
from firedrake import solving
from firedrake import ufl_expr
from firedrake import function
from firedrake.parloops import par_loop, READ, INC
import firedrake.variational_solver as vs

import numpy as np


__all__ = ['project', 'Projector']

# Store the solve function to use in a variable so external packages
# (dolfin-adjoint) can override it.
_solve = solving.solve


def project(v, V, bcs=None, mesh=None,
            solver_parameters=None,
            form_compiler_parameters=None,
            method="l2",
            name=None):
    """Project an :class:`.Expression` or :class:`.Function` into a :class:`.FunctionSpace`

    :arg v: the :class:`.Expression`, :class:`ufl.Expr` or
         :class:`.Function` to project
    :arg V: the :class:`.FunctionSpace` or :class:`.Function` to project into
    :arg bcs: boundary conditions to apply in the projection
    :arg mesh: the mesh to project into
    :arg solver_parameters: parameters to pass to the solver used when
         projecting.
    :arg form_compiler_parameters: parameters to the form compiler
    :arg method: a string denoting which type of projection to perform.
                 By default, "l2" is used, which is the standard Galerkin
                 projection. The other option would be to use the method
                 "average," which performs the projection using weighted
                 averages. This should only be used if you're projecting
                 from a discontinuous space to a continuous one. That is,
                 DG -> CG or Broken Raviart-Thomas -> Raviart-Thomas.
    :arg name: name of the resulting :class:`.Function`

    If ``V`` is a :class:`.Function` then ``v`` is projected into
    ``V`` and ``V`` is returned. If `V` is a :class:`.FunctionSpace`
    then ``v`` is projected into a new :class:`.Function` and that
    :class:`.Function` is returned.

    The ``mesh`` and ``form_compiler_parameters`` are currently ignored."""
    from firedrake import function

    if isinstance(V, functionspaceimpl.WithGeometry):
        ret = function.Function(V, name=name)
    elif isinstance(V, function.Function):
        ret = V
        V = V.function_space()
    else:
        raise RuntimeError(
            'Can only project into functions and function spaces, not %r'
            % type(V))

    if isinstance(v, expression.Expression):
        shape = v.value_shape()
        # Build a function space that supports PointEvaluation so that
        # we can interpolate into it.
        if isinstance(V.ufl_element().degree(), tuple):
            deg = max(V.ufl_element().degree())
        else:
            deg = V.ufl_element().degree()

        if v.rank() == 0:
            fs = functionspace.FunctionSpace(V.mesh(), 'DG', deg+1)
        elif v.rank() == 1:
            fs = functionspace.VectorFunctionSpace(V.mesh(), 'DG',
                                                   deg+1,
                                                   dim=shape[0])
        else:
            fs = functionspace.TensorFunctionSpace(V.mesh(), 'DG',
                                                   deg+1,
                                                   shape=shape)
        f = function.Function(fs)
        f.interpolate(v)
        v = f
    elif isinstance(v, function.Function):
        if v.function_space().mesh() != ret.function_space().mesh():
            raise RuntimeError("Can't project between mismatching meshes")
    elif not isinstance(v, ufl.core.expr.Expr):
        raise RuntimeError("Can only project from expressions and functions, not %r" % type(v))

    if v.ufl_shape != ret.ufl_shape:
        raise RuntimeError('Shape mismatch between source %s and target function spaces %s in project' %
                           (v.ufl_shape, ret.ufl_shape))

    if method == "l2":
        # Perform standard L2 projection
        p = ufl_expr.TestFunction(V)
        q = ufl_expr.TrialFunction(V)
        a = ufl.inner(p, q) * ufl.dx(domain=V.mesh())
        L = ufl.inner(p, v) * ufl.dx(domain=V.mesh())

        # Default to 1e-8 relative tolerance
        if solver_parameters is None:
            solver_parameters = {'ksp_type': 'cg', 'ksp_rtol': 1e-8}
        else:
            solver_parameters.setdefault('ksp_type', 'cg')
            solver_parameters.setdefault('ksp_rtol', 1e-8)

        _solve(a == L, ret, bcs=bcs,
               solver_parameters=solver_parameters,
               form_compiler_parameters=form_compiler_parameters)

    elif method == "average":
        # Loop over node extent and dof extent
        shapes = (V.finat_element.space_dimension(), np.prod(V.shape))
        accumulate_kernel = """
        for (int i=0; i<%d; ++i) {
            for (int j=0; j<%d; ++j) {
                vo[i][j] += v[i][j];
                w[i][j] += 1.0;
        }}""" % shapes

        # Ensure function we populate into is zeroed out
        ret.assign(0.0)
        w = function.Function(V)
        par_loop(accumulate_kernel, ufl.dx, {"vo": (ret, INC),
                                             "w": (w, INC),
                                             "v": (v, READ)})
        ret.dat /= w.dat

    else:
        raise ValueError("Method type %s not recognized" % str(method))

    return ret


class Projector(object):
    """
    A projector projects a UFL expression into a function space
    and places the result in a function from that function space,
    allowing the solver to be reused. Projection reverts to an assign
    operation if ``v`` is a :class:`.Function` and belongs to the same
    function space as ``v_out``.

    :arg v: the :class:`ufl.Expr` or
         :class:`.Function` to project
    :arg v_out: :class:`.Function` to put the result in
    :arg bcs: an optional set of :class:`.DirichletBC` objects to apply
              on the target function space.
    :arg solver_parameters: parameters to pass to the solver used when
         projecting.
    :arg method: a string denoting which type of projection to perform.
                 By default, "l2" is used, which is the standard Galerkin
                 projection. The other option would be to use the method
                 "average," which performs the projection using weighted
                 averages. This should only be used if you're projecting
                 from a discontinuous space to a continuous one. That is,
                 DG -> CG or Broken Raviart-Thomas -> Raviart-Thomas.
    """

    def __init__(self, v, v_out, bcs=None, solver_parameters=None,
                 constant_jacobian=True, method="l2"):

        if isinstance(v, expression.Expression) or \
           not isinstance(v, (ufl.core.expr.Expr, function.Function)):
            raise ValueError("Can only project UFL expression or Functions not '%s'" % type(v))

        self._same_fspace = (isinstance(v, function.Function) and v.function_space() ==
                             v_out.function_space())
        self.v = v
        self.v_out = v_out
        self.bcs = bcs
        self.method = method

        if self.method == "l2":
            if not self._same_fspace or self.bcs:
                V = v_out.function_space()

                p = ufl_expr.TestFunction(V)
                q = ufl_expr.TrialFunction(V)

                a = ufl.inner(p, q)*ufl.dx
                L = ufl.inner(p, v)*ufl.dx

                problem = vs.LinearVariationalProblem(a, L, v_out, bcs=self.bcs,
                                                      constant_jacobian=constant_jacobian)

                if solver_parameters is None:
                    solver_parameters = {}

                solver_parameters.setdefault("ksp_type", "cg")

                self.solver = vs.LinearVariationalSolver(problem,
                                                         solver_parameters=solver_parameters)
        elif self.method == "average":
            # NOTE: Any bcs on the function self.v should just work.
            # Loop over node extent and dof extent
            V = self.v_out.function_space()
            shapes = (V.finat_element.space_dimension(), np.prod(V.shape))
            self._accumulate_kernel = """
            for (int i=0; i<%d; ++i) {
                for (int j=0; j<%d; ++j) {
                    vo[i][j] += v[i][j];
                    w[i][j] += 1.0;
            }}""" % shapes

            self._w = function.Function(V)
        else:
            raise ValueError("Method type %s not recognized" % str(method))

    def project(self):
        """
        Apply the projection.
        """
        if self.method == "l2":
            if self._same_fspace and not self.bcs:
                self.v_out.assign(self.v)
            else:
                self.solver.solve()

        else:
            assert self.method == "average", (
                "Only 'l2' and 'average' are supported methods at this time."
            )
            # Ensure the functions we populate into are zeroed out
            self.v_out.assign(0.0)
            self._w.assign(0.0)
            par_loop(self._accumulate_kernel, ufl.dx, {"vo": (self.v_out, INC),
                                                       "w": (self._w, INC),
                                                       "v": (self.v, READ)})
            self.v_out.dat /= self._w.dat
            return self.v_out
