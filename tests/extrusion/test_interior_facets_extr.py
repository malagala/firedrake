from __future__ import absolute_import, print_function, division
import numpy as np
import pytest

from firedrake import *


def test_interior_facet_vfs_extr_horiz_2d_rhs():
    m = UnitIntervalMesh(1)
    mesh = ExtrudedMesh(m, layers=2)

    U = VectorFunctionSpace(mesh, 'DG', 1)
    v = TestFunction(U)
    n = FacetNormal(mesh)

    temp = assemble(jump(v, n)*dS_h).dat.data

    assert np.all(temp[:, 0] == 0.0)
    assert not np.all(temp[:, 1] == 0.0)


def test_interior_facet_vfs_extr_horiz_2d_lhs():
    m = UnitIntervalMesh(1)
    mesh = ExtrudedMesh(m, layers=2)

    U = VectorFunctionSpace(mesh, 'DG', 0)
    u = TrialFunction(U)
    v = TestFunction(U)
    n = FacetNormal(mesh)

    temp = assemble(avg(dot(u, n)*dot(v, n))*dS_h)

    assert temp.M.values[0, 0] == 0.0
    assert temp.M.values[1, 1] != 0.0
    assert temp.M.values[2, 2] == 0.0
    assert temp.M.values[3, 3] != 0.0


def test_interior_facet_vfs_extr_horiz_2d_mixed():
    m = UnitIntervalMesh(1)
    mesh = ExtrudedMesh(m, layers=2)

    U = VectorFunctionSpace(mesh, 'DG', 0)
    V = FunctionSpace(mesh, 'RTCF', 1)
    W = U*V

    u1, u2 = TrialFunctions(W)
    v1, v2 = TestFunctions(W)

    pp = assemble(dot(v1('+'), u2('+'))*dS_h)
    pm = assemble(dot(v1('+'), u2('-'))*dS_h)
    mp = assemble(dot(v1('-'), u2('+'))*dS_h)
    mm = assemble(dot(v1('-'), u2('-'))*dS_h)

    assert not np.all(pp.M[0, 1].values == pm.M[0, 1].values)
    assert not np.all(pp.M[0, 1].values == mp.M[0, 1].values)
    assert not np.all(pp.M[0, 1].values == mm.M[0, 1].values)
    assert not np.all(pm.M[0, 1].values == mp.M[0, 1].values)
    assert not np.all(pm.M[0, 1].values == mm.M[0, 1].values)
    assert not np.all(mp.M[0, 1].values == mm.M[0, 1].values)


def test_interior_facet_vfs_extr_horiz_3d_rhs():
    m = UnitSquareMesh(1, 1)
    mesh = ExtrudedMesh(m, layers=2)

    U = VectorFunctionSpace(mesh, 'DG', 1)
    v = TestFunction(U)
    n = FacetNormal(mesh)

    temp = assemble(jump(v, n)*dS_h).dat.data

    assert np.all(temp[:, 0] == 0.0)
    assert np.all(temp[:, 1] == 0.0)
    assert not np.all(temp[:, 2] == 0.0)


def test_interior_facet_vfs_extr_horiz_3d_lhs():
    m = UnitSquareMesh(1, 1)
    mesh = ExtrudedMesh(m, layers=2)

    U = VectorFunctionSpace(mesh, 'DG', 0)
    u = TrialFunction(U)
    v = TestFunction(U)
    n = FacetNormal(mesh)

    temp = assemble(avg(dot(u, n)*dot(v, n))*dS_h)

    assert temp.M.values[0, 0] == 0.0
    assert temp.M.values[1, 1] == 0.0
    assert temp.M.values[2, 2] != 0.0


def test_interior_facet_vfs_extr_vert_rhs():
    m = UnitIntervalMesh(2)
    mesh = ExtrudedMesh(m, layers=1)

    U = VectorFunctionSpace(mesh, 'DG', 1)
    v = TestFunction(U)
    n = FacetNormal(mesh)

    temp = assemble(jump(v, n)*dS_v).dat.data

    assert not np.all(temp[:, 0] == 0.0)
    assert np.all(temp[:, 1] == 0.0)


def test_interior_facet_vfs_extr_vert_lhs():
    m = UnitIntervalMesh(2)
    mesh = ExtrudedMesh(m, layers=1)

    U = VectorFunctionSpace(mesh, 'DG', 0)
    u = TrialFunction(U)
    v = TestFunction(U)
    n = FacetNormal(mesh)

    temp = assemble(avg(dot(u, n)*dot(v, n))*dS_v)

    assert temp.M.values[0, 0] != 0.0
    assert temp.M.values[1, 1] == 0.0
    assert temp.M.values[2, 2] != 0.0
    assert temp.M.values[3, 3] == 0.0


def test_interior_facet_vfs_extr_vert_mixed():
    m = UnitIntervalMesh(2)
    mesh = ExtrudedMesh(m, layers=1)

    U = VectorFunctionSpace(mesh, 'DG', 0)
    V = FunctionSpace(mesh, 'RTCF', 1)
    W = U*V

    u1, u2 = TrialFunctions(W)
    v1, v2 = TestFunctions(W)

    pp = assemble(dot(v1('+'), u2('+'))*dS_v)
    pm = assemble(dot(v1('+'), u2('-'))*dS_v)
    mp = assemble(dot(v1('-'), u2('+'))*dS_v)
    mm = assemble(dot(v1('-'), u2('-'))*dS_v)

    assert not np.all(pp.M[0, 1].values == pm.M[0, 1].values)
    assert not np.all(pp.M[0, 1].values == mp.M[0, 1].values)
    assert not np.all(pp.M[0, 1].values == mm.M[0, 1].values)
    assert not np.all(pm.M[0, 1].values == mp.M[0, 1].values)
    assert not np.all(pm.M[0, 1].values == mm.M[0, 1].values)
    assert not np.all(mp.M[0, 1].values == mm.M[0, 1].values)


if __name__ == '__main__':
    import os
    pytest.main(os.path.abspath(__file__))
