from distutils.core import setup
import py2exe


# We need to import the glob module to search for all files.
import glob

# We need to exclude matplotlib backends not being used by this executable.  You may find
# that you need different excludes to create a working executable with your chosen backend.
# We also need to include include various numerix libraries that the other functions call.

opts = {
  'py2exe': { "includes" : ["PyQt4", "numpy", "scipy", "pyqtgraph", "scipy.special._ufuncs_cxx", "scipy.interpolate.fitpack"],

                'excludes': ['_gtkagg', '_tkagg', '_agg2', '_cairo', '_cocoaagg', "Tcl", "Tkinter",
                             '_fltkagg', '_gtk','_gtkcairo' ]
              }
       }


# for console program use 'console = [{"script" : "scriptname.py"}]
setup(windows=[{"script" : "doctorGUIqtThread.py"}], options=opts)