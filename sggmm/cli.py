"""
Module containing the logic of the command line interface of the Supergiant Games Mod Manager
"""
import logging
import os
import re
import shutil
from pathlib import Path
from typing import List, Optional
from enum import StrEnum

import typer
from rich.logging import RichHandler
from typing_extensions import Annotated

logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler()]
    # handlers=[logging.FileHandler("cli.log", mode="w"), logging.StreamHandler()],
)

LOGGER = logging.getLogger(__name__)

REGEX_SUBSTITUTION: re.Pattern[str] = re.compile(
    r"|".join(
        [
            r"(\s?::.*?$\s?)",  # Single line comment
            r"(-:(?:.|\s)*?:-\s?)",  # Multiline comment
            r"(^\s+)",  # Empty lines and whitespace
        ]
    ),
    flags=re.MULTILINE,
)


class GameEnum(StrEnum):
    """Enum class for games"""

    HADES = "Hades"
    PYRE = "Pyre"
    TRANSISTOR = "Transistor"
    BASTION = "Bastion"

    @property
    def script_path(self) -> list[str]:
        """Path to the default script for each game

        Returns:
            list[str]: List of strings containing the default paths of each game
        """
        return {
            GameEnum.HADES: ["Scritps/RoomManager.lua"],
            GameEnum.PYRE: ["Scripts/Campaign.lua", "Scripts/MPScripts.lua"],
            GameEnum.TRANSISTOR: ["Scripts/AllCampaignScripts.txt"],
            GameEnum.BASTION: [""],
        }[self]

    @staticmethod
    def guess_game(game_path: Path):
        """Detect game by looking at the provided path

        Args:
            game_path (Path): Path to the game

        Returns:
            GameEnum: Specific game, defaulting to Hades
        """
        match game_path.parent.name:
            case "Hades":
                return GameEnum.HADES
            case "Pyre":
                return GameEnum.PYRE
            case "Transistor":
                return GameEnum.TRANSISTOR
            case "Bastion":
                return GameEnum.BASTION
            case _:
                return GameEnum.HADES


def uninstall_mods(game_path: Path, backup_path: Path, modfolder_path: Path):
    """Uninstalls mods and restores original content, if possible

    Args:
        game_path (Path): Path to the game
        backup_path (Path): Path to the backup folder
        modfolder_path (Path): Path to the mod folder

    Raises:
        typer.Exit: Exits the cli after uninstall
    """
    if backup_path.exists():
        if any(backup_path.iterdir()):
            LOGGER.info(
                'Restoring game files from backup folder "%s"',
                backup_path,
            )
            restore_files(game_path, backup_path)
        else:
            LOGGER.warning(
                'Backup folder "%s" is empty. Nothing to restore! Please validate your game files',
                backup_path,
            )
        LOGGER.info('Deleted backup folder "%s".', backup_path)
        shutil.rmtree(backup_path)
    else:
        LOGGER.warning(
            'Backup folder "%s" not found! Please validate your game files.',
            backup_path,
        )

    if modfolder_path.exists():
        shutil.rmtree(modfolder_path)
        LOGGER.info('Deleted mod folder "%s".', modfolder_path)

    raise typer.Exit()


def backup_files(file_list: List[Path], backup_path: Path) -> None:
    """Backup all provided files to the backup directory, creating folders if necessary

    Args:
        file_list (List[Path]): List of files to backup
        backup_path (Path): Path to the backup folder
    """
    for original_file in file_list:
        destination_path = backup_path.joinpath(
            original_file.relative_to(backup_path.parent)
        )

        if not destination_path.parent.exists():
            LOGGER.debug('Creating folder "%s"', destination_path.parent)
            destination_path.parent.mkdir(parents=True)
        if original_file.is_dir():
            destination_path.mkdir()
        else:
            LOGGER.debug('Copying file "%s" to "%s"', original_file, destination_path)
            shutil.copyfile(original_file, destination_path)


def restore_files(game_path: Path, backup_path: Path) -> None:
    """Traverse the backup folder and restore the original files to the game folder

    Args:
        game_path (Path): Path to the game files
        backup_path (Path): Path to the backup folder

    Returns:
        Set[Path]: Returns a set of all restored files
    """
    for item in backup_path.glob("**/*"):
        original_path = game_path.joinpath(item.relative_to(backup_path)).resolve()
        if original_path.is_dir():
            original_path.mkdir(parents=True, exist_ok=True)
        else:
            original_path.parent.mkdir(parents=True, exist_ok=True)

            try:
                shutil.copyfile(
                    item.resolve(), game_path.joinpath(item.relative_to(backup_path))
                )
                LOGGER.info('Restoring file "%s" to "%s".', backup_path, original_path)
            except shutil.SameFileError:
                LOGGER.warning(
                    'Files "%s" and "%s" are identical, skipping.',
                    backup_path,
                    original_path,
                )
            except OSError:
                LOGGER.error(
                    'Unable to restore file "%s"', original_path, exc_info=True
                )


def read_modfiles(modfolder_path: Path, game: GameEnum) -> List:
    """TODO
    Read modfiles and provide a changelist

    Args:
        modfolder_path (Path): Path to the modfolder

    Returns:
        List: Changelist
    """
    typer.echo(game.script_path)
    return []
    for modfile in modfolder_path.glob("**/modfile.txt"):
        with open(modfile, "r", encoding="utf-8-sig") as filehandle:
            LOGGER.debug('Reading modfile "%s"', modfile)
            file_content = filehandle.read()
            substituted_content = re.sub(REGEX_SUBSTITUTION, "", file_content)
            load_mods(substituted_content)

    return []


def load_mods(modfile_commands: str):
    """Load modfile commands and execute them

    Args:
        modfile_commands (str): modfile commands
    """
    for line in modfile_commands.splitlines():
        command, sub, *priority = line.split()
        match command.lower():
            case "load":
                LOGGER.debug(
                    "Loading the folloing imports with priority %d",
                    int(float(priority[0])),
                )
            case "import":
                LOGGER.debug("Importing %s", sub)
            case "to":
                LOGGER.debug(
                    "Changing destination for the following imports to %s", sub
                )
            case "top":
                LOGGER.debug("Importing %s at the top of file %s.", priority, "")
            case "xml":
                pass
            case "map":
                pass
            case "sjson":
                pass
            case "include":
                pass
            case _:
                LOGGER.warning('Command "%s" is not supported!', command)


def cli(
    game_path: Annotated[
        Path,
        typer.Argument(
            # exists=True,
            file_okay=False,
            writable=True,
            resolve_path=True,
            help="Path to the game folder",
        ),
    ] = Path(os.getcwd()),
    game: Annotated[
        Optional[GameEnum],
        typer.Option(
            "--game",
            "-g",
            help="Use the selected game",
            case_sensitive=False,
        ),
    ] = None,
    clean: Annotated[
        bool, typer.Option("--clean", "-c", help="Uninstall mods and exit.")
    ] = False,
    verbose: Annotated[
        bool, typer.Option("--verbose", "-v", help="Explain what is being done.")
    ] = False,
) -> None:
    """Supergiant Games Mod Manager helps you manage your mods for their games."""
    if verbose:
        LOGGER.setLevel(logging.DEBUG)

    backup_path = game_path.joinpath("Backup")
    modfolder_path = game_path.joinpath("Mods")

    detected_game = GameEnum.guess_game(game_path)

    if not game:
        game = detected_game

    if not (game == detected_game) and not typer.confirm(
        f"Selected game {game} does not match path {game_path}. Continue anyway?"
    ):
        raise typer.Abort

    if clean:
        uninstall_mods(game_path, backup_path, modfolder_path)

    if not modfolder_path.exists():
        LOGGER.warning('Mods folder "%s" does not exist!', modfolder_path)
        if typer.confirm(f"Create folder {modfolder_path}?", default=True):
            modfolder_path.mkdir()
            LOGGER.info(
                'Created mods folder "%s". Place your mods there and restart the application',
                modfolder_path,
            )
        raise typer.Exit()

    if not backup_path.exists():
        LOGGER.debug('Created backup folder "%s".', backup_path)
        backup_path.mkdir()

    read_modfiles(modfolder_path, game)
    # backup_files(list(game_path.joinpath("Scripts").glob("**/*")), backup_path)
    # apply_mods()


def main() -> None:
    """Run typer cli"""
    typer.run(cli)
