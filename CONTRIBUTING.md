# Contributing

This repository deploys the OSDU community Rock and Fluid Sample DDMS on Azure.
It tracks the
[community project](https://community.opengroup.org/osdu/platform/domain-data-mgmt-services/rock-and-fluid-sample/rafs-ddms-services)
in passthrough mode and adds the SPI repository contract.

> [!IMPORTANT]
> Code contributions are limited to Microsoft employees at this time. Anyone
> can report a bug or request a feature through
> [GitHub Issues](../../issues).

## Where a change belongs

| Area | Owner | Where to make the change |
|---|---|---|
| `.spi/`, `.github/upstream-filter.yml`, `CONTRIBUTING.md`, `README.md` | This repository | A pull request here |
| `.github/` except the files above, `build/`, `.release-please-config.json` | [`Azure/osdu-spi`](https://github.com/Azure/osdu-spi) | The template; template sync overwrites these files here |
| Application source, tests, and community deployment assets | OSDU community | The [community RAFS project](https://community.opengroup.org/osdu/platform/domain-data-mgmt-services/rock-and-fluid-sample/rafs-ddms-services); use the `port` label when a specific upstream fix must be brought in early |
| Azure infrastructure and Kubernetes runtime | [`Azure/osdu-spi-stack`](https://github.com/Azure/osdu-spi-stack) | The stack repository |

## Making a change

1. Branch from `main` with a type prefix such as `feat/`, `fix/`, or `chore/`.
2. Use Python 3.11 and run `.spi/ci/build.sh`.
3. Use [Conventional Commits](https://www.conventionalcommits.org/) for commits
   and the pull request title; release-please versions from them.
4. Open a pull request against `main`. Merging requires passing CodeQL and
   validation checks, resolved review threads, and the required approval.

## License

By contributing, you agree that your contributions will be licensed under the
[Apache License 2.0](LICENSE).
