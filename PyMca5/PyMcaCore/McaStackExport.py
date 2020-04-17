#/*##########################################################################
#
# The PyMca X-Ray Fluorescence Toolkit
#
# Copyright (c) 2020 European Synchrotron Radiation Facility
#
# This file is part of the PyMca X-ray Fluorescence Toolkit developed at
# the ESRF by the Software group.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#
#############################################################################*/
__author__ = "V.A. Sole - ESRF Data Analysis"
__contact__ = "sole@esrf.fr"
__license__ = "MIT"
__copyright__ = "European Synchrotron Radiation Facility, Grenoble, France"
import sys
import posixpath
import h5py
import logging
_logger = logging.getLogger(__name__)

def exportStackList(filename, stackList, channels=None, calibration=None):
    if isinstance(filename, h5py.File):
        h5 = filename
        ownFile = False
    else:
        h5 = h5py.File(filename, "w-")
        ownFile = True
    if hasattr(stackList, "data") and hasattr(stackList, "info"):
        stackList = [stackList]

    # initialize the entry
    entryName = "stack"
    entry = h5.require_group(entryName)
    entry.attrs["NX_class"] = u"NXentry"
    instrumentName = "instrument"
    instrument = entry.require_group(instrumentName)
    instrument.attrs["NX_class"] = u"NXinstrument"

    # save all the stacks
    dataTargets = []
    i = 0
    for stack in stackList:
        detectorName = "detector_%02d" % i
        detector = instrument.require_group(detectorName)
        detector.attrs["NX_class"] = u"detector"
        detectorPath = posixpath.join(entryName,instrumentName,detectorName)
        exportStack(stack,
                    h5,
                    detectorPath,
                    channels=channels,
                    calibration=calibration)
        if ownFile:
            h5.flush()
        dataPath = posixpath.join(detectorPath, "data")
        dataTargets.append(dataPath)
        i += 1

    # create NXdata
    measurement = entry.require_group("measurement")
    measurement.attrs["NX_class"] = u"NXdata"
    entry.attrs["default"] = u"measurement"
    i = 0
    auxiliary = []
    for target in dataTargets:
        name = posixpath.basename(posixpath.dirname(target))
        measurement[name] = h5py.SoftLink[target]
        if i == 0:
            measurement.attrs["signal"] = name
        else:
            auxiliary.append(name)
    if len(auxiliary):
        if sys.version_info < (3,):
            dtype = h5py.special_dtype(vlen=unicode)
        else:
            dtype = h5py.special_dtype(vlen=str)
        measurement.attrs["auxiliary_signals"] = numpy.array(auxiliary,
                                                             dtype=dtype)
    if ownFile:
        h5.flush()
        h5.close()

def exportStack(stack, h5object, path, channels=None, calibration=None):
    """
    Exports the stack to the given HDF5 file object and path
    """
    if not H5PY:
        raise ImportError("h5py not available")
    h5g = h5object.require_group(path)

    # destination should be an NXdetector group
    att = "NX_class"
    if att not in h5g.attrs:
        h5g.attrs[att] = u"NXdetector"
    elif h5g.attrs[att] != u"NXdetector":
        _logger.warning("Invalid destination NXclass %s" % h5g.attrs[att])

    # put the data themselves
    data = stack.data
    dataset = h5g.require_dataset("data",
                                  shape=data.shape,
                                  dtype=data.dtype)
    dataset[:] = data

    # provide a hint for the data type
    info = stack.info
    mcaIndex = info.get('McaIndex', -1)
    if mcaIndex < 0:
        mcaIndex = len(data.shape) + mcaIndex
    if len(data.shape) > 1:
        if mcaIndex == 0:
            if len(data.shape) == 3:
                data.attrs["interpretation"] = u"image"
        else:
            data.attrs["interpretation"] = u"spectrum"

    # get the calibration
    if calibration is None:
        calibration = info.get('McaCalib', [0.0, 1.0, 0.0])
    h5g["calibration"] = numpy.array(calibration, copy=False)

    # get the time
    for key in ["McaLiveTime", "live_time"]:
        if info.get(key, None):
            # TODO: live time can actually be elapsed time!!!
            h5g["live_time"] =  numpy.array(info[key], copy=False)

    for key in ["preset_time", "elapsed_time"]:
        if info.get(key, None):
            h5g[key] =  numpy.array(info[key], copy=False)

    # get the channels
    if channels is None:
        if hasattr(stack, "x"):
            if hasattr(stack.x, "__len__"):
                if len(stack.x):
                    channels = stack.x[0]

    if channels:
        h5g["channels"] = numpy.array(channels, copy=False)

    # the positioners
    if info.get("positioners", None):
        posGroupPath = posixpath.join(posixpath.dirname(path),
                                      "positioners")
        posGroup = h5object.require_group(posGroupPath)
        att = "NX_class"
        if att not in posGroup.attrs:
            posGroup.attrs[att] = u"NXcollection"
        for key in info["positioners"]:
            if key not in posGroup:
                posGroup[key] = numpy.array(info[key], copy=False)
