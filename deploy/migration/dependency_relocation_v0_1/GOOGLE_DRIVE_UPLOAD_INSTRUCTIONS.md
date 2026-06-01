# Google Drive Upload Instructions

Target folder:

```text
https://drive.google.com/drive/folders/1PwybNATp-pPZ8DJiTEJbga3mJO1p4NCn
```

Connector status:

```text
The connected Google Drive tool could not access this folder ID.
No upload was performed by Codex.
```

Upload package:

```text
/home/taiji_admin/Taiji_Hub/Taiji_Governance/system_info/Taiji_Dependency_Cloud_Readonly_20260512.tar.gz
```

Staging folder:

```text
/home/taiji_admin/Taiji_Hub_Org_Readonly_Cloud_Staging/Taiji_Dependency_Cloud_Readonly_20260512
```

Manual upload rule:

- Upload only the tar.gz or the staging folder contents.
- Do not upload `keys/`, `.env`, DB volumes, D member vault, raw logs, or secrets.
- Keep Drive permission read-only unless explicitly approved.
- Record upload completion in audit.

