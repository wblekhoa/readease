"""Static ReadEase origin marker with no user or installation data."""

PROVENANCE_SCHEMA_VERSION = 1
PROVENANCE_ID = "READEASE-THU-AM-NC-2026-01"
LICENSE_ID = "PolyForm-Noncommercial-1.0.0"
REQUIRED_NOTICE = (
    "Required Notice: Copyright © 2026 Lê Khoa. "
    "ReadEase — Thư Âm original scaffold. "
    "Provenance ID READEASE-THU-AM-NC-2026-01. "
    "Noncommercial use only under PolyForm Noncommercial 1.0.0."
)


def provenance_payload() -> dict[str, object]:
    """Return the deterministic public provenance record for every build."""

    return {
        "schema_version": PROVENANCE_SCHEMA_VERSION,
        "product": "ReadEase — Thư Âm",
        "provenance_id": PROVENANCE_ID,
        "license_id": LICENSE_ID,
        "required_notice": REQUIRED_NOTICE,
        "scope": "first-party-software-and-scaffold",
        "tracking": False,
    }


def apply_provenance(application: object) -> None:
    """Expose provenance as hidden Qt application properties without I/O."""

    set_property = getattr(application, "setProperty")
    set_property("ReadEaseProvenanceID", PROVENANCE_ID)
    set_property("ReadEaseLicenseIdentifier", LICENSE_ID)
    set_property("ReadEaseRequiredNotice", REQUIRED_NOTICE)
    set_property("ReadEaseProvenanceTracking", False)
