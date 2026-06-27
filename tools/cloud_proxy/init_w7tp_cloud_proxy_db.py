#!/usr/bin/env python3
from w7tp_openwebui_cloud_proxy import main
import sys
sys.argv.append("--init-db")
raise SystemExit(main())
