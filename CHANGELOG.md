# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Changed

- **Immutable datasets with WPC versioning (#707):** Each bulk data POST now creates a new
  immutable dataset (unique dataset ID) and a new WPC record version. Dataset IDs are no longer
  reused across updates; previous bulk data is preserved through OSDU's built-in WPC versioning.
- **GET data with version suffix (#707):** GET endpoints accept an optional `record_id:version`
  suffix (e.g., `opendes:work-product-component--SamplesAnalysis:my-record:3`) to retrieve
  historical bulk data. Omitting the version returns the latest data, preserving backward
  compatibility.
