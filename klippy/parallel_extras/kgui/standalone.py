#!/usr/bin/env python3
import os
import site
site.addsitedir(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
os.environ["KGUI_TESTING"] = "True"
import kgui

kgui.mainApp(None).run()
