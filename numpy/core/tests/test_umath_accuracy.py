import numpy as np
import platform
from os import path
import sys
import pytest
from ctypes import c_float, c_int, cast, pointer, POINTER
from numpy.testing import assert_array_max_ulp
from numpy.core._multiarray_umath import __cpu_features__

IS_AVX = __cpu_features__.get('AVX512F', False) or \
        (__cpu_features__.get('FMA3', False) and __cpu_features__.get('AVX2', False))
runtest = sys.platform.startswith('linux') and IS_AVX
platform_skip = pytest.mark.skipif(not runtest,
                                   reason="avoid testing inconsistent platform "
                                   "library implementations")

# convert string to hex function taken from:
# https://stackoverflow.com/questions/1592158/convert-hex-to-float #
def convert(s):
    i = int(s, 16)                   # convert from hex to a Python int
    cp = pointer(c_int(i))           # make this into a c integer
    fp = cast(cp, POINTER(c_float))  # cast the int pointer to a float pointer
    return fp.contents.value         # dereference the pointer, get the float

str_to_float = np.vectorize(convert)
files = ['umath-validation-set-exp',
         'umath-validation-set-log',
         'umath-validation-set-sin',
         'umath-validation-set-cos']

class TestAccuracy:
    @platform_skip
    def test_validate_transcendentals(self):
        with np.errstate(all='ignore'):
            for filename in files:
                data_dir = path.join(path.dirname(__file__), 'data')
                filepath = path.join(data_dir, filename)
                with open(filepath) as fid:
                    file_without_comments = (r for r in fid if not r[0] in ('$', '#'))
                    data = np.genfromtxt(file_without_comments,
                                         dtype=('|S39','|S39','|S39',int),
                                         names=('type','input','output','ulperr'),
                                         delimiter=',',
                                         skip_header=1)
                    npfunc = getattr(np, filename.split('-')[3])
                    for datatype in np.unique(data['type']):
                        data_subset = data[data['type'] == datatype]
                        inval  = np.array(str_to_float(data_subset['input'].astype(str)), dtype=eval(datatype))
                        outval = np.array(str_to_float(data_subset['output'].astype(str)), dtype=eval(datatype))
                        perm = np.random.permutation(len(inval))
                        inval = inval[perm]
                        outval = outval[perm]
                        maxulperr = data_subset['ulperr'].max()
                        assert_array_max_ulp(npfunc(inval), outval, maxulperr)

    def test_ignore_nan_ulperror(self):
        # Ignore ULP differences between various NAN's
        nan1_f32 = np.array(str_to_float('0xffffffff'), dtype=np.float32)
        nan2_f32 = np.array(str_to_float('0x7fddbfbf'), dtype=np.float32)
        assert_array_max_ulp(nan1_f32, nan2_f32, 0)
