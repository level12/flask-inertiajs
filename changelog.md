# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
This project uses [Calendar Versioning](https://calver.org/): `MAJOR.YYYYMMDD.SEQUENCE`.
The major version identifies breaking changes; the sequence distinguishes releases on
the same day.


## [Unreleased]


## [0.20261125.1] - 2026-11-25


### Added

- Handle 301, 303, 307, and 308 redirects to external URLs and non-Inertia endpoints
  as full-page navigations.
- Convert internal 301 redirects to 303 after PUT, PATCH, DELETE, and QUERY requests
  so the follow-up request uses GET.


## [0.20261124.1] - 2026-11-24


### Added

- Initial release of the Inertia v3 adapter for Flask, including Pydantic support,
  shared props, validation errors, flash messages, redirects, and asset versioning.

[Unreleased]: https://github.com/level12/flask-inertiajs/compare/v0.20261125.1...HEAD
[0.20261125.1]: https://github.com/level12/flask-inertiajs/compare/v0.20261124.1...v0.20261125.1
[0.20261124.1]: https://github.com/level12/flask-inertiajs/releases/tag/v0.20261124.1
