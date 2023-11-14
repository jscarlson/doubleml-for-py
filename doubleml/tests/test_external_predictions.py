import numpy as np
import pytest
import math
from sklearn.linear_model import LinearRegression, LassoCV, LogisticRegression
from doubleml import DoubleMLPLR, DoubleMLIRM, DoubleMLData
from doubleml.datasets import make_plr_CCDDHNR2018, make_irm_data
from doubleml.utils import dummy_regressor, dummy_classifier


@pytest.fixture(scope="module", params=["IV-type", "partialling out"])
def plr_score(request):
    return request.param

@pytest.fixture(scope="module", params=["ATE", "ATTE"])
def irm_score(request):
    return request.param


@pytest.fixture(scope="module", params=["dml1", "dml2"])
def dml_procedure(request):
    return request.param


@pytest.fixture(scope="module", params=[1, 3])
def n_rep(request):
    return request.param


@pytest.fixture(scope="module")
def doubleml_plr_fixture(plr_score, dml_procedure, n_rep):
    ext_predictions = {"d": {}}

    x, y, d = make_plr_CCDDHNR2018(n_obs=500, dim_x=20, alpha=0.5, return_type="np.array")

    np.random.seed(3141)

    dml_data = DoubleMLData.from_arrays(x=x, y=y, d=d)

    kwargs = {"obj_dml_data": dml_data, "score": plr_score, "n_rep": n_rep, "dml_procedure": dml_procedure}

    if plr_score == "IV-type":
        kwargs["ml_g"] = LinearRegression()

    DMLPLR = DoubleMLPLR(ml_m=LinearRegression(), ml_l=LinearRegression(), **kwargs)
    np.random.seed(3141)

    DMLPLR.fit(store_predictions=True)

    ext_predictions["d"]["ml_m"] = DMLPLR.predictions["ml_m"][:, :, 0]
    ext_predictions["d"]["ml_l"] = DMLPLR.predictions["ml_l"][:, :, 0]

    if plr_score == "IV-type":
        kwargs["ml_g"] = dummy_regressor()
        ext_predictions["d"]["ml_g"] = DMLPLR.predictions["ml_g"][:, :, 0]

    DMLPLR_ext = DoubleMLPLR(ml_m=dummy_regressor(), ml_l=dummy_regressor(), **kwargs)

    np.random.seed(3141)
    DMLPLR_ext.fit(external_predictions=ext_predictions)

    res_dict = {"coef_normal": DMLPLR.coef, "coef_ext": DMLPLR_ext.coef}

    return res_dict


@pytest.fixture(scope="module")
def doubleml_irm_fixture(irm_score, dml_procedure, n_rep):
    ext_predictions = {"d": {}}

    x, y, d = make_irm_data(n_obs=500, dim_x=20, theta=0.5, return_type="np.array")

    np.random.seed(3141)

    dml_data = DoubleMLData.from_arrays(x=x, y=y, d=d)

    kwargs = {"obj_dml_data": dml_data, "score": irm_score, "n_rep": n_rep, "dml_procedure": dml_procedure}

    DMLIRM = DoubleMLIRM(ml_g=LinearRegression(), ml_m=LogisticRegression(), **kwargs)
    np.random.seed(3141)

    DMLIRM.fit(store_predictions=True)

    ext_predictions["d"]["ml_g0"] = DMLIRM.predictions["ml_g0"][:, :, 0]
    ext_predictions["d"]["ml_g1"] = DMLIRM.predictions["ml_g1"][:, :, 0]
    ext_predictions["d"]["ml_m"] = DMLIRM.predictions["ml_m"][:, :, 0]

    DMLIRM_ext = DoubleMLIRM(ml_g=dummy_regressor(), ml_m=dummy_classifier(), **kwargs)

    np.random.seed(3141)
    DMLIRM_ext.fit(external_predictions=ext_predictions)

    res_dict = {"coef_normal": DMLIRM.coef, "coef_ext": DMLIRM_ext.coef}

    return res_dict


@pytest.mark.ci
def test_doubleml_plr_coef(doubleml_plr_fixture):
    assert math.isclose(
        doubleml_plr_fixture["coef_normal"], doubleml_plr_fixture["coef_ext"], rel_tol=1e-9, abs_tol=1e-4
    )
    
@pytest.mark.ci
def test_doubleml_irm_coef(doubleml_irm_fixture):
    assert math.isclose(
        doubleml_irm_fixture["coef_normal"], doubleml_irm_fixture["coef_ext"], rel_tol=1e-9, abs_tol=1e-4
    )
