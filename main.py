import io
import math
import time
import tkinter as tk
from pathlib import Path
from tkinter import PhotoImage

import cairosvg
import numpy as np
from PIL import Image, ImageTk
from faker import Faker

NUMBER_OF_PLAYERS = 100
IMAGE_SIZE = 100
PADDING = 10
SIMULATE_ROLLS = 100000
MESSAGE_LINE_LENGTH = 100
FPS = 30


def apply_red_shade(image: PhotoImage) -> PhotoImage:
    pil_image = ImageTk.getimage(image)
    if pil_image.mode != "RGB" and pil_image.mode != "RGBA":
        pil_image = pil_image.convert("RGBA" if pil_image.mode == "LA" or "A" in pil_image.mode else "RGB")

    data = np.array(pil_image)
    if pil_image.mode == "RGBA":
        mask = (data[:, :, 0] < 10) & (data[:, :, 1] < 10) & (data[:, :, 2] < 10) & (data[:, :, 3] > 0)
        data[mask] = [255, 0, 0, 255]
    else:
        mask = (data[:, :, 0] < 10) & (data[:, :, 1] < 10) & (data[:, :, 2] < 10)
        data[mask] = [255, 0, 0]
    red_image = Image.fromarray(data, pil_image.mode)

    return ImageTk.PhotoImage(red_image)


def svg_to_photoimage(file_path: Path, size: tuple[int, int]) -> PhotoImage:
    png_data = cairosvg.svg2png(url=str(file_path))
    image = Image.open(io.BytesIO(png_data))
    image_resized = image.resize(size)
    return ImageTk.PhotoImage(image_resized)


class Player:
    def __init__(self, name: str) -> None:
        self.name_field = tk.StringVar(value=name)
        self.score_field = tk.StringVar(value="Score: 0 points\n")
        self.score = 0
        self.roll = 0
        self.dice_image_label: tk.Label | None = None

    def __str__(self) -> str:
        return self.name

    def __repr__(self) -> str:
        return self.name

    @property
    def name(self) -> str:
        return self.name_field.get()

    @name.setter
    def name(self, value: str) -> None:
        self.name_field.set(value)


class DiceRollerGame:
    def __init__(self, root_window: tk.Tk, number_of_players: int = NUMBER_OF_PLAYERS) -> None:
        self.root = root_window
        self.root.title("Dice Roller")
        self.result_label: tk.Label | None = None

        self.players: list[Player] = []

        image_size = IMAGE_SIZE, IMAGE_SIZE
        self.dice_images = [svg_to_photoimage(Path(f"icons/dice_{i}.svg"), image_size) for i in range(0, 6 + 1)]
        self.winning_dice_images = [apply_red_shade(image) for image in self.dice_images]
        self.number_of_players_field = tk.StringVar()

        self.number_of_players_field.trace_add("write", self.update_number_of_players)
        self.number_of_players_field.set(str(number_of_players))

    def render_ui(self) -> None:
        for widget in self.root.winfo_children():
            widget.grid_forget()

        number_rows = round(math.sqrt(len(self.players)))
        number_columns = math.ceil(len(self.players) / number_rows) if len(self.players) > 3 else 3

        self.result_label = tk.Label(self.root, text="")
        self.result_label.grid(row=0, columnspan=number_columns, padx=PADDING, pady=PADDING)

        tk.Entry(self.root, textvariable=self.number_of_players_field).grid(row=1, column=0, padx=PADDING, pady=PADDING)

        tk.Button(self.root, text="Roll the Dice!", command=self.next_turn).grid(row=1, column=1, padx=PADDING, pady=PADDING)
        tk.Button(self.root, text=f"Simulate {SIMULATE_ROLLS} rolls", command=lambda: self.simulate_rolls(SIMULATE_ROLLS)).grid(
            row=1, column=2, padx=PADDING, pady=PADDING
        )

        for index, player in enumerate(self.players):
            row = (index // number_columns) + 2
            column = index % number_columns
            row *= 3

            player.dice_image_label = tk.Label(self.root, image=self.dice_images[0])
            player.dice_image_label.grid(row=row, column=column, padx=PADDING, pady=PADDING)
            tk.Label(self.root, textvariable=player.score_field).grid(row=row + 1, column=column, padx=PADDING, pady=PADDING)
            tk.Entry(self.root, textvariable=player.name_field).grid(
                row=row + 2, column=column, padx=PADDING, pady=PADDING, sticky="W"
            )

    def update_number_of_players(self, *_args) -> None:
        try:
            new_number_of_players = int(self.number_of_players_field.get())
        except ValueError:
            return
        if new_number_of_players > 0:
            fake = Faker()
            self.players = [Player(fake.name()) for _ in range(new_number_of_players)]
            self.render_ui()

    def get_high_score(self) -> int:
        return max(player.score for player in self.players)

    def next_turn(self, update_ui: bool = True) -> None:
        self.roll_dice(update_ui)
        winners = self.get_winners()

        for winner in winners:
            winner.score += 1

        if update_ui:
            for winner in winners:
                winner.dice_image_label.config(image=self.winning_dice_images[winner.roll])

        if update_ui:
            high_score = self.get_high_score()

            for player in self.players:
                high_score_text = " * High Score! * " if player.score == high_score else ""
                player.score_field.set(f"Score: {player.score} points" + "\n" + high_score_text)

            names = ", ".join(w.name for w in winners[:-1]) + (" and " if len(winners) > 1 else "") + winners[-1].name
            result_message = f"{names} won the round!"
            while len(last_line := result_message.splitlines()[-1]) > MESSAGE_LINE_LENGTH:
                last_space_position_in_last_line = last_line.rfind(" ", 0, MESSAGE_LINE_LENGTH)
                last_space_position_in_message = len(result_message) - len(last_line) + last_space_position_in_last_line
                result_message = (
                    result_message[:last_space_position_in_message] + "\n" + result_message[last_space_position_in_message + 1 :]
                )
            while result_message.count("\n") < 3:
                result_message += "\n"
            self.result_label.config(text=result_message)

    def roll_dice(self, update_ui: bool) -> None:
        rolls = np.random.randint(1, 7, len(self.players))
        for player, roll in zip(self.players, rolls):
            player.roll = roll
            if update_ui:
                player.score_field.value = f"Score: {player.score} points"
                player.dice_image_label.config(image=self.dice_images[player.roll])

    def get_winners(self) -> list[Player]:
        high_roller = max(self.players, key=lambda player: player.roll)
        high_roll = high_roller.roll
        return [player for player in self.players if player.roll == high_roll]

    def simulate_rolls(self, iterations: int = 100):
        frame_time = 1 / FPS
        last_ui_updated = time.time()

        for index in range(iterations):
            elapsed_time = time.time() - last_ui_updated
            if elapsed_time < frame_time:
                self.next_turn(update_ui=False)
            else:
                self.next_turn()
                self.root.update()
                last_ui_updated = time.time()
        self.root.quit()


if __name__ == "__main__":
    root = tk.Tk()
    app = DiceRollerGame(root)
    app.render_ui()
    # root.after(0, app.simulate_rolls, SIMULATE_ROLLS)

    root.mainloop()
    pass
