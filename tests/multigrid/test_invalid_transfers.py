from __future__ import absolute_import, print_function, division
from firedrake import *
import pytest


@pytest.mark.parametrize("transfer",
                         [prolong, inject, restrict])
def test_transfer_invalid_level_combo(transfer):
    m = UnitIntervalMesh(10)
    mh = MeshHierarchy(m, 2)
    coarse = Function(FunctionSpace(mh[0], "DG", 0))
    fine = Function(FunctionSpace(mh[-1], "DG", 0))
    if transfer == prolong:
        input, output = fine, coarse
    else:
        input, output = coarse, fine
    with pytest.raises(ValueError):
        transfer(input, output)


@pytest.mark.parametrize("transfer",
                         [prolong, inject, restrict])
def test_transfer_mismatching_functionspace(transfer):
    m = UnitIntervalMesh(10)
    mh = MeshHierarchy(m, 2)
    coarse = Function(FunctionSpace(mh[0], "DG", 0))
    fine = Function(FunctionSpace(mh[1], "CG", 1))
    if transfer == prolong:
        input, output = coarse, fine
    else:
        input, output = fine, coarse
    with pytest.raises(ValueError):
        transfer(input, output)


if __name__ == "__main__":
    import os
    pytest.main(os.path.abspath(__file__))
