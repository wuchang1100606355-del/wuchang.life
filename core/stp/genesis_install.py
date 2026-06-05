from core.stp.manifest \
    import load_manifest

from core.stp.manifest \
    import save_manifest

from core.stp.genesis_builder \
    import build_genesis

def install_genesis():

    manifest = load_manifest()

    manifest["genesis"] = \
        build_genesis()

    save_manifest(
        manifest
    )

    return manifest["genesis"]
