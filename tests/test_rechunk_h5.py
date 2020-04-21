# -*- coding: utf-8 -*-
"""
pytests for  Rechunk h5
"""
import h5py
import numpy as np
import os
import pytest

from rex.resource import Resource
from rex.rechunk_h5.rechunk_h5 import (get_dataset_attributes,
                                       to_records_array, RechunkH5)
from rex import TESTDATADIR

PURGE_OUT = True


def create_var_attrs(h5_file):
    """
    Create DataFrame for rechunk attributes

    Parameters
    ----------
    h5_file : str
        Source .h5 file

    Returns
    -------
    var_attrs : pandas.DataFrame
        rechunk variable attributes
    """
    var_attrs = get_dataset_attributes(h5_file)
    t_chunk = 8 * 7 * 24
    for var, _ in var_attrs.iterrows():
        if var == 'time_index':
            var_attrs.loc[var, 'dtype'] = 'S20'
            var_attrs.at[var, 'attrs'] = {'freq': 'h', 'timezone': 'UTC'}
        elif var == 'meta':
            var_attrs.loc[var, 'chunks'] = None
            var_attrs.loc[var, 'dtype'] = None
        else:
            var_attrs.loc[var, 'chunks'] = (t_chunk, 10)

    return var_attrs


def check_rechunk(src, dst, missing=None):
    """
    Compare src and dst .h5 files
    """
    with h5py.File(dst, mode='r') as f_dst:
        with h5py.File(src, mode='r') as f_src:
            for dset in f_dst:
                assert dset in f_src
                ds_dst = f_dst[dset]
                ds_src = f_src[dset]
                assert ds_dst.shape == ds_src.shape
                if dset != 'time_index':
                    assert ds_dst.dtype == ds_src.dtype

                chunks = ds_dst.chunks
                if chunks is not None:
                    assert chunks != ds_src.chunks

            if missing is not None:
                for dset in missing:
                    assert dset in f_src
                    assert dset not in f_dst


def test_to_records_array():
    """
    Test converstion of pandas DataFrame to numpy records array for .h5
    ingestion
    """
    path = os.path.join(TESTDATADIR, 'wtk/ri_100_wtk_2012.h5')
    with Resource(path) as f:
        meta = f.meta
        truth = f.h5['meta'][...]

    test = to_records_array(meta)

    for c in truth.dtype.names:
        msg = "{} did not get converted propertly!".format(c)
        assert np.all(test[c] == truth[c]), msg


@pytest.mark.parametrize('drop', [None,
                                  ['pressure_0m', ],
                                  ['pressure_100m',
                                   'temperature_100m',
                                   'windspeed_100m']])
def test_rechunk_h5(drop):
    """
    Test RechunkH5
    """
    src_path = os.path.join(TESTDATADIR, 'wtk/ri_100_wtk_2012.h5')
    rechunk_path = os.path.join(TESTDATADIR, 'wtk/rechunk.h5')
    var_attrs = create_var_attrs(src_path)
    if drop is not None:
        var_attrs = var_attrs.drop(drop)

    RechunkH5.run(src_path, rechunk_path, var_attrs)

    check_rechunk(src_path, rechunk_path, missing=drop)

    if PURGE_OUT:
        os.remove(rechunk_path)
