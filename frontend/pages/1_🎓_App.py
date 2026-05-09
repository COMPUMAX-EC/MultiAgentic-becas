# Re-export: this page runs the main scholarship search app
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
exec(open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app.py")).read())
