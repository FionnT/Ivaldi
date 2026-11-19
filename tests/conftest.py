import random
import shutil
import string
from pathlib import Path

import pytest

temp = Path(__file__).parent / "testing_tmp"


@pytest.fixture(scope="session", autouse=True)
def create_test_temp():
    temp.mkdir(exist_ok=True, parents=True)
    yield
    shutil.rmtree(temp)


@pytest.fixture(scope="function", autouse=True)
def temp_path():

    random_path = "".join(random.choice(string.ascii_uppercase + string.digits) for _ in range(8))
    test_temp = temp / random_path
    test_temp.mkdir(exist_ok=True, parents=True)

    yield test_temp
    shutil.rmtree(str(test_temp))
