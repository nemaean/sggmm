import nox


@nox.session(reuse_venv=True)
def tests(session: nox.Session) -> None:
    session.install(
        "pytest",
    )
    session.run("pytest", "tests")
