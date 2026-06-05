from core.stp.manifest \
    import load_manifest

from core.stp.manifest \
    import save_manifest

def append_packet(packet):

    manifest = load_manifest()

    manifest["packets"].append(
        packet
    )

    save_manifest(
        manifest
    )

    return len(
        manifest["packets"]
    )
