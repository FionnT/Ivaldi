from ivaldi import main


def test_main_dispatches_run_and_forwards_only_application_arguments(monkeypatch):
    captured = {}

    def run(location, args):
        captured["args"] = args
        return 17

    monkeypatch.setattr("ivaldi._run", run)

    result = main(["run", "--verbose", "--output", "some file.txt"])

    assert result == 17
    assert captured["args"] == ["--verbose", "--output", "some file.txt"]
