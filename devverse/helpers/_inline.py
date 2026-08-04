# -*- coding: utf-8 -*-
# Copyright (c) 2025 Delete_ee
# Licensed under the MIT License.
# This file is part of Delete_ee


from pyrogram import types

from devverse import app, config, lang
from devverse.core.lang import lang_codes


class Inline:
    def __init__(self):
        self.ikm = types.InlineKeyboardMarkup
        self.ikb = types.InlineKeyboardButton

    def cancel_dl(self, text) -> types.InlineKeyboardMarkup:
        return self.ikm([[self.ikb(text=text, callback_data=f"cancel_dl")]])

    def controls(
        self,
        chat_id: int,
        status: str = None,
        timer: str = None,
        remove: bool = False,
    ) -> types.InlineKeyboardMarkup:
        keyboard = []
        if status:
            keyboard.append(
                [self.ikb(text=status, callback_data=f"controls status {chat_id}")]
            )
        elif timer:
            keyboard.append(
                [self.ikb(text=timer, callback_data=f"controls status {chat_id}")]
            )

        if not remove:
            keyboard.append(
                [
                    self.ikb(text="⏪ 10s", callback_data=f"controls seek_back {chat_id}"),
                    self.ikb(text="10s ⏩", callback_data=f"controls seek_forward {chat_id}"),
                ]
            )
            keyboard.append(
                [
                    self.ikb(text="▶️", callback_data=f"controls resume {chat_id}"),
                    self.ikb(text="⏸️", callback_data=f"controls pause {chat_id}"),
                    self.ikb(text="🔄", callback_data=f"controls replay {chat_id}"),
                    self.ikb(text="⏭️", callback_data=f"controls skip {chat_id}"),
                    self.ikb(text="⏹️", callback_data=f"controls stop {chat_id}"),
                ]
            )

        return self.ikm(keyboard)


    def help_markup(
        self, _lang: dict, back: bool = False
    ) -> types.InlineKeyboardMarkup:
        if back:
            rows = [
                [
                    self.ikb(text=_lang["back"], callback_data="help back"),
                    self.ikb(text=_lang["close"], callback_data="help close"),
                ]
            ]
        else:
            cbs = ["admins", "auth", "blist", "lang", "ping", "play", "queue", "stats", "sudo"]
            buttons = [
                self.ikb(text=_lang[f"help_{i}"], callback_data=f"help {cb}")
                for i, cb in enumerate(cbs)
            ]
            rows = [buttons[i : i + 3] for i in range(0, len(buttons), 3)]
            rows.append([
                self.ikb(text="CHANNEL", url=config.SUPPORT_CHANNEL),
                self.ikb(text="SUPPORT", url=config.SUPPORT_CHAT),
            ])


        return self.ikm(rows)


    def lang_markup(self, _lang: str) -> types.InlineKeyboardMarkup:
        langs = lang.get_languages()

        buttons = [
            self.ikb(
                text=f"{name} ({code}) {'✔️' if code == _lang else ''}",
                callback_data=f"lang_change {code}",
            )
            for code, name in langs.items()
        ]
        rows = [buttons[i : i + 2] for i in range(0, len(buttons), 2)]
        return self.ikm(rows)

    def ping_markup(self, text: str) -> types.InlineKeyboardMarkup:
        return self.ikm([[self.ikb(text=text, url=config.SUPPORT_CHANNEL)]])

    def play_queued(
        self, chat_id: int, item_id: str, _text: str
    ) -> types.InlineKeyboardMarkup:
        return self.ikm(
            [
                [
                    self.ikb(
                        text=_text, callback_data=f"controls force {chat_id} {item_id}"
                    )
                ]
            ]
        )

    def queue_markup(
        self, chat_id: int, _text: str, playing: bool
    ) -> types.InlineKeyboardMarkup:
        _action = "pause" if playing else "resume"
        return self.ikm(
            [[self.ikb(text=_text, callback_data=f"controls {_action} {chat_id} q")]]
        )

    def settings_markup(
        self, lang: dict, admin_only: bool, cmd_delete: bool, language: str, chat_id: int
    ) -> types.InlineKeyboardMarkup:
        on  = "✅ ON"
        off = "❌ OFF"
        return self.ikm(
            [
                [
                    self.ikb(
                        text=lang["play_mode"] + " ➜",
                        callback_data=f"settings noop {chat_id}",
                    ),
                    self.ikb(
                        text=on if admin_only else off,
                        callback_data=f"settings play {chat_id}",
                    ),
                ],
                [
                    self.ikb(
                        text=lang["cmd_delete"] + " ➜",
                        callback_data=f"settings noop {chat_id}",
                    ),
                    self.ikb(
                        text=on if cmd_delete else off,
                        callback_data=f"settings delete {chat_id}",
                    ),
                ],
                [
                    self.ikb(
                        text=lang["language"] + " ➜",
                        callback_data=f"settings noop {chat_id}",
                    ),
                    self.ikb(
                        text="🌐 " + lang_codes.get(language, language).upper(),
                        callback_data=f"language {chat_id}",
                    ),
                ],
                [
                    self.ikb(text=lang["back"], callback_data="help back"),
                    self.ikb(text=lang["close"], callback_data="help close"),
                ],
            ]
        )


    def start_key(
        self, lang: dict, private: bool = False
    ) -> types.InlineKeyboardMarkup:
        rows = [
            [
                self.ikb(
                    text="➕ ADD ME TO YOUR GROUP",
                    url=f"https://t.me/{app.username}?startgroup=true",
                )
            ],
            [
                self.ikb(text="📜 COMPLETE CMDS", callback_data="help"),
                self.ikb(text="⚙️ SETTINGS", callback_data="settings")
            ],
            [
                self.ikb(text="👑 OWNER", url=f"https://t.me/{config.OWNER_USERNAME}"),
                self.ikb(text="📢 UPDATES", url=config.SUPPORT_CHANNEL),
            ],
        ]
        if not private:
            rows.append([self.ikb(text=lang["language"], callback_data="language")])
        return self.ikm(rows)



    def yt_key(self, link: str) -> types.InlineKeyboardMarkup:
        return self.ikm(
            [
                [
                    self.ikb(text="SHARE", copy_text=link),
                    self.ikb(text="YOUTUBE", url=link),
                ],
            ]
        )

