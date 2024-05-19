import argparse
import filecmp
import os
import shutil
import json
from collections import defaultdict

from utils import read_json_file, copytree_with_progress

MANIFEST_DIR = r"C:\ProgramData\Epic\EpicGamesLauncher\Data\Manifests"

LOCATION_OPTIONS = [
    r"C:\Program Files (x86)\Epic Games\games",
    r"D:\Games\Epic Games",  # Frequently played
    r"E:\Games\Epic Games",  # Infrequently played
    r"Z:\Games\Epic Games"  # Won't play
]


def get_games_by_base_dir():
    games_by_base_dir = defaultdict(list)

    for item_file in os.listdir(MANIFEST_DIR):
        if item_file.endswith('.item'):
            manifest_path = os.path.join(MANIFEST_DIR, item_file)
            manifest_data = read_json_file(manifest_path)
            game_id = manifest_data['InstallationGuid']
            game_name = manifest_data['DisplayName']
            install_dir = manifest_data['InstallLocation']
            base_install_dir = os.path.dirname(install_dir)
            game_tuple = (game_id, game_name, install_dir)
            games_by_base_dir[base_install_dir].append(game_tuple)

    for root_location, game_tuple in games_by_base_dir.items():
        game_tuple.sort(key=lambda x: x[1].lower())

    global_game_index = 1
    for root_location, game_tuple in games_by_base_dir.items():
        for index, game in enumerate(game_tuple, start=1):
            game_tuple[index-1] = (global_game_index,) + game
            global_game_index += 1

    return games_by_base_dir


def list_games(games_by_base_dir):
    print("GAMES BY ROOT INSTALL LOCATION:")
    for root_location, game_tuple in games_by_base_dir.items():
        print(f"\nRoot Install Location: {root_location}")
        for (index, game_id, game_name, install_dir) in game_tuple:
            print(f"  {index}. {game_id} - {game_name}")


def update_manifest(game_id, new_install_dir):
    manifest_path = os.path.join(MANIFEST_DIR, game_id + ".item")
    shutil.copyfile(manifest_path, f'{manifest_path}.bak')

    manifest_data = read_json_file(manifest_path)
    manifest_data['InstallLocation'] = new_install_dir
    manifest_data['StagingLocation'] = os.path.join(new_install_dir, '.egstore/bps')
    manifest_data['ManifestLocation'] = os.path.join(new_install_dir, '.egstore')

    with open(manifest_path, 'w') as file:
        json.dump(manifest_data, file, indent=4)


def move_game(game_id, desired_base_dir):
    manifest_path = os.path.join(MANIFEST_DIR, game_id + ".item")
    manifest_data = read_json_file(manifest_path)

    source_install_dir = manifest_data['InstallLocation']
    new_install_dir = os.path.join(
        desired_base_dir,
        os.path.basename(source_install_dir)
    )
    
    if not os.path.exists(source_install_dir) or not os.listdir(source_install_dir):
        print("Source install directory is empty. Aborting move operation.")
        return
    
    if os.path.abspath(source_install_dir) != os.path.abspath(new_install_dir):
        print(f"Copying from {source_install_dir} to {new_install_dir}")
        copytree_with_progress(source_install_dir, new_install_dir)
        dircmp = filecmp.dircmp(source_install_dir, new_install_dir, ignore=None)

        if not dircmp.left_only and not dircmp.right_only:
            print("\nCopy successful, updating manifest and removing old install location.")
            update_manifest(game_id, new_install_dir)
            shutil.rmtree(source_install_dir)
        else:
            print("\nERROR: File comparison mismatch:")
            print("Left only: ", dircmp.left_only if dircmp.left_only else "None")
            print("Right only: ", dircmp.right_only if dircmp.right_only else "None")
            
            print("\nRemoving new install location.")
            if os.path.exists(new_install_dir):
                shutil.rmtree(new_install_dir)
    else:
        print("\nPreferred location is the same as the current location. No action required.")


def move_all_games(desired_base_dir, games_by_base_dir):
    for root_location, game_tuple in games_by_base_dir.items():
        for (global_game_index, game_id, game_name, install_dir) in game_tuple:
            move_game(game_id, desired_base_dir)


def interactive(games_by_base_dir):
    list_games(games_by_base_dir)

    selected_index = input("\nEnter the index number of the game you want to update or 'all' to move all games: ")

    if selected_index.lower() == 'all':
        for index, location in enumerate(LOCATION_OPTIONS, start=1):
            print(f"{index}. Option {index}: {location}")

        try:
            desired_option = int(input(f"\nEnter your choice (1-{len(LOCATION_OPTIONS)}): "))
            if 1 <= desired_option <= len(LOCATION_OPTIONS):
                desired_base_dir = LOCATION_OPTIONS[desired_option - 1]
                move_all_games(desired_base_dir, games_by_base_dir)
            else:
                print("ERROR: Invalid choice. Exiting.")
        except ValueError:
            print("ERROR: Invalid input. Please enter a valid choice.")
    else:
        try:
            selected_index = int(selected_index)
            selected_game_id, selected_game_name, selected_install_dir = None, None, None
            for root_location, game_tuple in games_by_base_dir.items():
                for (global_game_index, game_id, game_name, install_dir) in game_tuple:
                    if global_game_index == selected_index:
                        selected_game_id, selected_game_name, selected_install_dir = game_id, game_name, install_dir
                        break

            if selected_game_id:
                print(f"\nSelected Game:")
                print(f"Game ID: {selected_game_id}")
                print(f"Game Name: {selected_game_name}")
                print(f"Current Install Location: {selected_install_dir}")

                print("\nChoose a preferred installation location option:")

                for index, location in enumerate(LOCATION_OPTIONS, start=1):
                    print(f"{index}. Option {index}: {location}")

                try:
                    desired_option = int(input(f"\nEnter your choice (1-{len(LOCATION_OPTIONS)}): "))
                    if 1 <= desired_option <= len(LOCATION_OPTIONS):
                        desired_base_dir = LOCATION_OPTIONS[desired_option - 1]
                        move_game(selected_game_id, desired_base_dir)
                    else:
                        print("ERROR: Invalid choice. Exiting.")
                except ValueError:
                    print("ERROR: Invalid input. Please enter a valid choice.")
            else:
                print("ERROR: Invalid Game ID.")
        except ValueError:
            print("ERROR: Invalid input. Please enter a valid index number or 'all'.")


def main():
    parser = argparse.ArgumentParser(description="Epic Games Library Manager CLI")
    subparsers = parser.add_subparsers(title="subcommands", dest="command")

    subparsers.add_parser("list", help="List all games currently recognized by Epic Games.")

    move_parser = subparsers.add_parser("move", help="Move a game to a different location.")
    move_parser.add_argument("game_id", help="Game ID to move.")
    move_parser.add_argument("desired_base_dir", help="Desired base directory.")

    args = parser.parse_args()

    if args.command == "list":
        games_by_base_dir = get_games_by_base_dir()
        list_games(games_by_base_dir)
    elif args.command == "move":
        move_game(args.game_id, args.desired_base_dir)
    else:
        print("No command provided, running in interactive mode.")
        games_by_base_dir = get_games_by_base_dir()
        interactive(games_by_base_dir)


if __name__ == "__main__":
    main()
