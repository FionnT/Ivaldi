# Repository Coverage

[Full report](https://htmlpreview.github.io/?https://github.com/FionnT/Ivaldi/blob/python-coverage-comment-action-data/htmlcov/index.html)

| Name                         |    Stmts |     Miss |   Cover |   Missing |
|----------------------------- | -------: | -------: | ------: | --------: |
| ivaldi/\_\_init\_\_.py       |       59 |        0 |    100% |           |
| ivaldi/\_\_main\_\_.py       |        2 |        0 |    100% |           |
| ivaldi/commands/build.py     |       15 |        0 |    100% |           |
| ivaldi/commands/install.py   |       24 |        0 |    100% |           |
| ivaldi/commands/run.py       |       18 |        0 |    100% |           |
| ivaldi/commands/uninstall.py |       16 |        1 |     94% |        19 |
| ivaldi/shared/admin.py       |       61 |        3 |     95% |     78-80 |
| ivaldi/shared/alias.py       |      138 |        4 |     97% |162, 176-178 |
| ivaldi/shared/build.py       |      128 |        0 |    100% |           |
| ivaldi/shared/collect.py     |       70 |        0 |    100% |           |
| ivaldi/shared/extract.py     |       26 |        0 |    100% |           |
| ivaldi/shared/project.py     |       58 |        0 |    100% |           |
| ivaldi/shared/python.py      |       46 |        0 |    100% |           |
| ivaldi/shared/settings.py    |      189 |        1 |     99% |       209 |
| ivaldi/shared/uv.py          |      100 |        2 |     98% |     53-54 |
| ivaldi/types/enums.py        |       66 |        0 |    100% |           |
| ivaldi/types/settings.py     |       95 |        1 |     99% |         8 |
| **TOTAL**                    | **1111** |   **12** | **99%** |           |


## Setup coverage badge

Below are examples of the badges you can use in your main branch `README` file.

### Direct image

[![Coverage badge](https://raw.githubusercontent.com/FionnT/Ivaldi/python-coverage-comment-action-data/badge.svg)](https://htmlpreview.github.io/?https://github.com/FionnT/Ivaldi/blob/python-coverage-comment-action-data/htmlcov/index.html)

This is the one to use if your repository is private or if you don't want to customize anything.

### [Shields.io](https://shields.io) Json Endpoint

[![Coverage badge](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/FionnT/Ivaldi/python-coverage-comment-action-data/endpoint.json)](https://htmlpreview.github.io/?https://github.com/FionnT/Ivaldi/blob/python-coverage-comment-action-data/htmlcov/index.html)

Using this one will allow you to [customize](https://shields.io/endpoint) the look of your badge.
It won't work with private repositories. It won't be refreshed more than once per five minutes.

### [Shields.io](https://shields.io) Dynamic Badge

[![Coverage badge](https://img.shields.io/badge/dynamic/json?color=brightgreen&label=coverage&query=%24.message&url=https%3A%2F%2Fraw.githubusercontent.com%2FFionnT%2FIvaldi%2Fpython-coverage-comment-action-data%2Fendpoint.json)](https://htmlpreview.github.io/?https://github.com/FionnT/Ivaldi/blob/python-coverage-comment-action-data/htmlcov/index.html)

This one will always be the same color. It won't work for private repos. I'm not even sure why we included it.

## What is that?

This branch is part of the
[python-coverage-comment-action](https://github.com/marketplace/actions/python-coverage-comment)
GitHub Action. All the files in this branch are automatically generated and may be
overwritten at any moment.