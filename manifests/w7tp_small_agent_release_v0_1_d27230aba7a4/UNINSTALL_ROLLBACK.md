# W7TP Small Agent Candidate Uninstall and Rollback

This package is `CANDIDATE_DEPLOYABLE`; it is not a claim of completed production deployment.

Rollback restores the previously recorded user-level `current` target with an atomic link switch, then runs the packaged healthcheck. The previous release is retained.

Uninstall disables only the user-level `w7tp-small-agent` service and removes its `current` link after operator confirmation. Versioned release directories, configuration, and state are retained unless a separate authorized cleanup is performed.

No step requires root access or changes a firewall, router, database, Active Canonical, or Pointer. Secrets must not be stored in this release or its configuration.
