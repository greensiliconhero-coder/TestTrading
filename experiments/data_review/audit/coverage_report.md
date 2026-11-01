# Coverage findings

Counts below use actual timestamps, not filename labels.

## Daily

- Entire absent years within observed range: [2020]

| Year | Symbols with data | Symbol-days |
|---|---:|---:|
| 2015 | 47 | 11611 |
| 2016 | 47 | 11564 |
| 2017 | 49 | 11702 |
| 2018 | 49 | 12006 |
| 2019 | 49 | 12005 |
| 2021 | 49 | 12152 |
| 2022 | 49 | 12152 |
| 2023 | 49 | 12054 |
| 2024 | 49 | 12201 |
| 2025 | 49 | 9261 |

## Minute

- Entire absent years within observed range: [2020]

| Year | Symbols with data | Symbol-days |
|---|---:|---:|
| 2015 | 25 | 5470 |
| 2016 | 25 | 5950 |
| 2017 | 26 | 6230 |
| 2018 | 26 | 6396 |
| 2019 | 25 | 5978 |
| 2021 | 49 | 12152 |
| 2022 | 49 | 12152 |
| 2023 | 49 | 12054 |
| 2024 | 49 | 11995 |
| 2025 | 49 | 9261 |

## Next decisions

1. Investigate absent years with the provider/downloader. Do not interpolate entire missing periods.
2. Establish why the instrument universe differs over time before selecting a common research sample.
3. Confirm corporate-action adjustments and official daily close conventions before treating cross-frequency differences as bad data.
4. A model should not be trained until material numeric errors and duplicate timestamps are resolved explicitly.
5. Preserve a final chronological holdout and record proposed horizons before comparing model performance.
