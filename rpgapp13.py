import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk
import json
import random
import os

# --- 1. データモデル層 ---

class Skill:
    def __init__(self, name, mp_cost, power, effect_type, duration=0):
        self.name = name
        self.mp_cost = mp_cost
        self.power = power
        self.effect_type = effect_type
        self.duration = duration

class Character:
    def __init__(self, name, job, hp, mp, atk, description, skills=None, image_path="images/chara.png",level=1,exp=0):
        self.name = name
        self.job = job
        self.hp = hp
        self.max_hp = hp
        self.mp = mp
        self.max_mp = mp
        self.atk = atk
        self.description = description
        self.image_path = image_path if os.path.exists(image_path) else "images/chara.png"
        self.level = level
        self.exp = exp
        # スキル文字列をオブジェクトに変換
        # 動的なステータス
        self.atk_modifier = 0  # 攻撃力の増減量
        self.buff_turns = 0    # バフの残りターン
        self.is_defending = False
        
        self.raw_skills = skills if skills else []
        self.skills = []
        for s_name in self.raw_skills:
            # 名前から効果を推測する簡易ロジック
            if "ヒール" in s_name or "回復" in s_name:
                self.skills.append(Skill(s_name, 15, 30, "heal"))
            elif "ガード" in s_name or "防御" in s_name or"プロテクション" in s_name:
                self.skills.append(Skill(s_name, 5, 0, "defense"))
            elif "パワー" in s_name or "強化" in s_name or"エンブレム" in s_name:
                self.skills.append(Skill(s_name, 12, 10, "buff", duration=3))
            elif "弱体" in s_name or "カース" in s_name:
                self.skills.append(Skill(s_name, 12, -5, "debuff", duration=3))
            else:
                self.skills.append(Skill(s_name, 10, self.atk + 10, "damage"))

    @property
    def current_atk(self):
        """現在の攻撃力を計算（基本値 + 修正値）"""
        return max(1, self.atk + self.atk_modifier)

    def is_alive(self):
        return self.hp > 0

    def to_dict(self):
        """セーブ用に辞書形式へ変換"""
        return {
            "name": self.name, "job": self.job, "hp": self.hp,
            "mp": self.mp, "atk": self.atk,"level": self.level, 
            "exp": self.exp, "description": self.description,
            "skills": self.raw_skills, "image_path": self.image_path
        }
    
    def gain_exp(self, amount):
        """経験値を獲得し、レベルアップ判定を行う"""
        self.exp += amount
        leveled_up = False
        up_stats = {"hp": 0, "mp": 0, "atk": 0}
        
        # 次のレベルに必要な経験値 (例: レベル * 100)
        next_exp = self.level * 100
        
        while self.exp >= next_exp:
            self.level += 1
            self.exp -= next_exp
            leveled_up = True
            
            # ステータス上昇値の計算（ジョブごとに変えるのもアリ）
            h_up = random.randint(10, 20)
            m_up = random.randint(5, 10)
            a_up = random.randint(2, 5)
            
            self.max_hp += h_up
            self.hp = self.max_hp # レベルアップ時は全快
            self.max_mp += m_up
            self.mp = self.max_mp
            self.atk += a_up
            
            up_stats["hp"] += h_up
            up_stats["mp"] += m_up
            up_stats["atk"] += a_up
            
            next_exp = self.level * 100 # 次のレベルへ
            
        return leveled_up, up_stats
# --- 2. 確認：詳細表示ウィンドウ ---
class DetailWindow(tk.Toplevel):
    def __init__(self, parent, character, side_color="#e0f0ff"):
        super().__init__(parent)
        self.title(f"データ照会: {character.name}")
        self.geometry("400x600")
        self.configure(bg=side_color)

        tk.Label(self, text=f"【{character.job}】", font=("Arial", 10)).pack(pady=5)
        tk.Label(self, text=character.name, font=("MS Gothic", 18, "bold"), bg=side_color).pack()
        
        # 画像表示
        self.canvas = tk.Canvas(self, width=200, height=200, bg="white", highlightthickness=0)
        self.canvas.pack(pady=10)
        try:
            img = Image.open(character.image_path).resize((200, 200))
            self.photo = ImageTk.PhotoImage(img)
            self.canvas.create_image(100, 100, image=self.photo)
        except:
            self.canvas.create_text(100, 100, text="No Image")

        # ステータス
        stats_frame = tk.Frame(self, bg="white", padx=10, pady=10)
        stats_frame.pack(fill="x", padx=20)
        tk.Label(stats_frame, text=f"HP: {character.hp}/{character.max_hp}", bg="white").pack(anchor="w")
        tk.Label(stats_frame, text=f"MP: {character.mp}/{character.max_mp}", bg="white").pack(anchor="w")
        tk.Label(stats_frame, text=f"ATK: {character.atk}", bg="white").pack(anchor="w")
        tk.Label(stats_frame, text=f"スキル: {', '.join(character.raw_skills)}", bg="white", wraplength=300).pack(anchor="w", pady=5)
        tk.Label(stats_frame, text=f"レベル: {character.level}", bg="white").pack(anchor="w")

        # 特徴
        tk.Label(self, text="― 特徴 ―", bg=side_color).pack(pady=5)
        tk.Label(self, text=character.description, wraplength=280, bg=side_color, justify="left").pack(padx=20)
        
        tk.Button(self, text="閉じる", command=self.destroy).pack(pady=15)

# --- 2. 戦闘：スキル選択GUIウィンドウ ---

class BattleWindow(tk.Toplevel):
    def __init__(self, app_instance, party, enemy_templates):
        super().__init__(app_instance.root)
        self.app = app_instance
        self.title("BATTLE: vs Multiple Enemies")
        self.geometry("1000x750")
        
        # 敵を実体化
        self.enemies = [Character(**e.to_dict()) for e in enemy_templates]
        self.party = party
        self.current_hero = self.party[0]
        self.pending_action = None  # 選択されたスキルを一時保存する用    
        self.setup_battle_ui()
        self.update_ui()

    def setup_battle_ui(self):
        # --- 敵表示エリア（動的に作成） ---
        self.enemy_frame = tk.LabelFrame(self, text=" 敵軍団 ")
        self.enemy_frame.pack(pady=10, fill="x", padx=20)

        self.enemy_bars = []
        self.enemy_labels = []

        for i, en in enumerate(self.enemies):
            frame = tk.Frame(self.enemy_frame)
            frame.pack(fill="x", pady=10)
            lbl = tk.Label(frame, text=f"{en.name}", width=20)
            lbl.pack(side="left")
            bar = ttk.Progressbar(frame, length=200, maximum=en.max_hp)
            bar.pack(side="left", padx=20)
            bar["value"] = en.hp
            self.enemy_labels.append(lbl)
            self.enemy_bars.append(bar)
        self.refresh_enemy_display()

        # ログエリア
        self.log_text = tk.Text(self, height=10, width=60, state='disabled', bg="#1a1a1a", fg="#00ff00")
        self.log_text.pack(pady=10)

        # プレイヤー情報
        self.hero_info = tk.Label(self, text="", font=("bold", 11))
        self.hero_info.pack()

        # コマンドエリア
        self.cmd_frame = tk.LabelFrame(self, text=" 行動を選択 ")
        self.cmd_frame.pack(pady=10, fill="x", padx=20)
        
        self.refresh_buttons()
        self.update_ui()

    def add_log(self, msg):
        self.log_text.config(state='normal')
        self.log_text.insert(tk.END, msg + "\n")
        self.log_text.see(tk.END)
        self.log_text.config(state='disabled')

    def update_ui(self):
        """戦闘画面の全情報を最新状態に更新する"""
        
        # 1. 味方（自分）の情報を更新
        hero = self.current_hero
        # バフ状態をアイコンで表現
        buff_icon = "🔥" if hero.atk_modifier > 0 else ""
        def_icon = "🛡️" if hero.is_defending else ""
        
        status_text = (
            f"[Lv.{hero.level}]  {hero.name}\n "
            f"(HP: {hero.hp}/{hero.max_hp}, MP: {hero.mp}/{hero.max_mp})\n "
            f"{hero.exp} exp 状態: {buff_icon}{def_icon} 正常"
        )
        self.hero_info.config(text=status_text)
        if hasattr(self.master, "update_after_battle"):
            self.master.update_after_battle()
        # 2. 敵軍団の情報（HPバーとラベル）を更新
        self.refresh_enemy_display()

        # 3. 決着がついている場合はボタンを無効化するなどの制御
        if all(not e.is_alive() for e in self.enemies) or not hero.is_alive():
            for btn in self.cmd_frame.winfo_children():
                btn.config(state="disabled")
    def refresh_buttons(self):
        """キャラに合わせてスキルボタンを生成"""
        for w in self.cmd_frame.winfo_children(): w.destroy()
        normal_atk = Skill("通常攻撃", 0, self.current_hero.atk, "damage")
        tk.Button(self.cmd_frame, text="通常攻撃", command=lambda: self.prepare_action(normal_atk)).pack(side="left", padx=5)
        for s in self.current_hero.skills:
            # ターゲットが必要なスキル（攻撃・デバフ）だけを抽出
            if s.effect_type in ["damage", "debuff"]:
                btn = tk.Button(self.cmd_frame, text=s.name, 
                                command=lambda sk=s: self.prepare_action(sk))
                btn.pack(side="left", padx=5)
            elif s.effect_type in ["heal", "defense", "buff"]:
                # 回復は自分にかけるので即実行
                btn = tk.Button(self.cmd_frame, text=s.name, command=lambda sk=s: self.prepare_action(sk))
                btn.pack(side="left", padx=5)
        tk.Button(self.cmd_frame, text="交代", bg="#eee", command=self.open_switch).pack(side="right", padx=5)

    # --- ステップ1: 技を「予約」してターゲット選択へ ---
    def prepare_action(self, skill):
        if self.current_hero.mp < skill.mp_cost:
            messagebox.showwarning("MP不足", "MPが足りません！")
            return
        
        self.pending_action = skill
        
        # 効果タイプによって「敵を選ぶか」「味方を選ぶか」を分岐
        if skill.effect_type in ["damage", "debuff"]:
            self.show_enemy_target_selection()
        elif skill.effect_type in ["heal", "buff", "defense"]:
            self.show_ally_target_selection()

# --- ターゲット選択のフロー ---
    # --- ステップ2: ターゲットを選ばせる（サブウィンドウ） ---
    def show_enemy_target_selection(self):
        target_win = tk.Toplevel(self)
        target_win.title(f"{self.pending_action.name} の対象を選択")
        
        tk.Label(target_win, text="どの敵を狙いますか？").pack(pady=5)
        
        for en in self.enemies:
            if en.is_alive():
                btn = tk.Button(target_win, text=f"{en.name} (HP:{en.hp})", width=25,
                                command=lambda target=en, w=target_win: self.execute_pending_action(target, w))
                btn.pack(pady=2, padx=10)
    # --- ステップ2: 味方を選択させるウィンドウ ---
    def show_ally_target_selection(self):
        target_win = tk.Toplevel(self)
        target_win.title(f"{self.pending_action.name} の対象を選択")
        
        tk.Label(target_win, text="誰に使用しますか？").pack(pady=5, padx=20)
        
        # パーティーメンバー全員をボタンとして表示
        for member in self.party:
            # 戦闘不能のキャラにバフをかけられないようにする場合
            state = "normal" if member.is_alive() else "disabled"
            
            btn = tk.Button(target_win, text=f"{member.name} (HP:{member.hp})", 
                            width=25, state=state,
                            command=lambda m=member, w=target_win: self.execute_ally_action(m, w))
            btn.pack(pady=3, padx=10)
    # --- ステップ3: 技の実行 ---
    def execute_pending_action(self, target, window):
        window.destroy()  # 選択窓を閉じる
        skill = self.pending_action
        self.current_hero.mp -= skill.mp_cost
        
        if skill.effect_type == "damage":
            dmg = skill.power + random.randint(-3, 3)
            target.hp -= dmg
            self.add_log(f"> {self.current_hero.name}の{skill.name}！ {target.name}に{dmg}のダメージ！")
        
        elif skill.effect_type == "debuff":
            # デバフ処理（例：攻撃力を下げる）
            target.atk_modifier -= 5 
            self.add_log(f"DOWN! {target.name}の攻撃力が下がった！")

        self.update_ui() # ダメージやデバフの結果をすぐに反映
        self.on_turn_end()  # ターン終了処理を呼び出す
        self.pending_action = None # 予約クリア
        self.check_battle_status()
    def check_battle_status(self):
        self.update_ui()

        # 1. 勝利判定（すべての敵が死亡）
        if all(not e.is_alive() for e in self.enemies):
            self.add_log("★ 敵軍を殲滅しました！")
            self.show_victory_result()
            return True
        else:
            self.after(800, self.enemies_turn)

        return False
    def enemies_turn(self):
        """生きている敵が順番に攻撃してくる"""
        for en in self.enemies:
            if en.is_alive() and self.current_hero.is_alive():
                dmg = en.atk
                # 防御判定
                if self.current_hero.is_defending:
                    dmg //= 2
                    self.add_log(f"🛡 防御効果！ ダメージを軽減した！")
                    self.current_hero.is_defending = False # 一度受けたら解除
                self.current_hero.hp -= dmg
                self.add_log(f"<!> {en.name}の攻撃！ {dmg}のダメージ！")
        self.update_ui()
        if not self.current_hero.is_alive():
            self.add_log(f"× {self.current_hero.name}は力尽きた...")

        if all(not p.is_alive() for p in self.party):
            self.show_defeat_result()
            return True

# --- ステップ3: 味方への実行処理 ---
    def execute_ally_action(self, target, window):
        window.destroy()
        skill = self.pending_action
        self.current_hero.mp -= skill.mp_cost
        
        if skill.effect_type == "heal":
            heal_amt = skill.power
            target.hp = min(target.max_hp, target.hp + heal_amt)
            self.add_log(f"💚 {self.current_hero.name}の{skill.name}！ {target.name}のHPが{heal_amt}回復！")
            
        elif skill.effect_type == "buff":
            target.atk_modifier = skill.power
            target.buff_turns = skill.duration
            self.add_log(f"🔥 {target.name}に{skill.name}！ 攻撃力が上がった！")

        elif skill.effect_type == "defense":
            target.is_defending = True
            self.add_log(f"🛡 {target.name}は{skill.name}で守りを固めた！")

        self.pending_action = None
        self.update_ui()
        self.on_turn_end() # ターン終了処理へ
        
        # 味方の行動が終わったので敵のターンへ
        self.after(800, self.enemies_turn)

    def on_turn_end(self):
        """ターン終了時の状態更新処理"""
        
        # --- 1. 味方のバフ・防御状態の更新 ---
        hero = self.current_hero
        
        # 防御は1ターンで解除（敵の攻撃を受けた直後、または自分の行動終了時）
        if hero.is_defending:
            # ログに出すと煩雑な場合は、内部処理のみでOK
            hero.is_defending = False

        # バフのカウントダウン
        if hero.buff_turns > 0:
            hero.buff_turns -= 1
            if hero.buff_turns == 0:
                hero.atk_modifier = 0 # 攻撃力補正をリセット
                self.add_log(f"🔔 {hero.name}の攻撃力アップ効果が終了した。")
            self.update_ui()
        # --- 2. 全ての敵のデバフ状態の更新 ---
        for en in self.enemies:
            if en.is_alive() and en.buff_turns > 0:
                en.buff_turns -= 1
                if en.buff_turns == 0:
                    en.atk_modifier = 0 # デバフ（攻撃力減少など）をリセット
                    self.add_log(f"✨ {en.name}の弱体化状態が回復した。")
                

        # UIの数値を最新状態にする
        self.update_ui()

        # --- 3. 次のフェーズへ ---
        # 敵がまだ生きているなら、敵のターンを開始
        if any(e.is_alive() for e in self.enemies):
            # 少し間を置いてから敵の攻撃を開始（演出用）
            self.after(800, self.enemies_turn)

    def refresh_enemy_display(self):
        """敵のHPバーとラベルを最新の状態に更新する"""
        for i, en in enumerate(self.enemies):
            # 1. HPバーの更新（最小0、最大値を下回らないように調整）
            current_hp = max(0, en.hp)
            self.enemy_bars[i]["value"] = current_hp
            
            # 2. ステータスラベルの更新
            if not en.is_alive():
                # 倒れている場合はグレーアウトして「撃破」と表示
                self.enemy_labels[i].config(
                    text=f"💀 {en.name} (撃破)", 
                    fg="#888888"
                )
            else:
                # 生きている場合は現在のHP数値を表示
                # バフ・デバフがかかっている場合にアイコンを出す演出もここで可能
                status_icons = ""
                if en.atk_modifier > 0: status_icons += " 🔺" # バフ
                if en.atk_modifier < 0: status_icons += " 🔻" # デバフ
                
                self.enemy_labels[i].config(
                    text=f"👾 {en.name} [HP: {current_hp}/{en.max_hp}]{status_icons}",
                    fg="black"
                )
        pass

    def show_victory_result(self):
        """勝利リザルト画面を表示し、経験値を分配する"""
        # 1. 獲得経験値の計算（例：敵の攻撃力の合計 × 10）
        total_exp = sum(en.atk for en in self.enemies) * 10
        
        # リザルト専用のサブウィンドウ
        result_win = tk.Toplevel(self)
        result_win.title("戦闘勝利")
        result_win.geometry("400x500")
        result_win.grab_set() # この画面を閉じるまで他を操作不能にする

        tk.Label(result_win, text="✨ VICTORY ✨", font=("MS Gothic", 20, "bold"), fg="#D4AF37").pack(pady=15)
        tk.Label(result_win, text=f"獲得経験値: {total_exp} EXP", font=("bold", 12)).pack(pady=5)

        # 2. 生存している味方に経験値を分配
        alive_members = [p for p in self.party if p.is_alive()]
        if not alive_members: return # 全滅時は呼ばれない想定だが念のため
        
        exp_per_person = total_exp // len(alive_members)

        for p in self.party:
            # 内部データ（Characterクラス）の経験値を増やし、レベルアップ判定
            leveled_up, up_stats = p.gain_exp( exp_per_person)

            # 各キャラの結果を表示する枠
            char_frame = tk.Frame(result_win, relief="groove", bd=2, padx=10, pady=5)
            char_frame.pack(fill="x", padx=20, pady=5)
            
            # 名前と獲得EXP
            txt = f"{p.name} は {exp_per_person} EXP 獲得！"
            color = "black"
            
            if leveled_up:
                # レベルアップ時の強調表示
                txt += f" → Lv.{p.level} に上がった！"
                color = "blue"
                details = f"最大HP +{up_stats['hp']} / 最大MP +{up_stats['mp']} / 攻撃力 +{up_stats['atk']}"
                tk.Label(char_frame, text=details, fg="green", font=("small-caption", 9)).pack(side="bottom")
            
            tk.Label(char_frame, text=txt, fg=color, font=("bold", 10)).pack(side="top", anchor="w")

        # 3. 終了ボタン（ここから finish_battle を呼ぶ）
        tk.Button(result_win, text="キャンプへ戻る", font=("bold", 12),
                  bg="#4CAF50", fg="white", width=20,
                  command=self.finish_battle).pack(pady=20)

    def finish_battle(self):
        """戦闘結果（成長と消耗）を確定させ、メイン画面へ戻る"""


        # 1. 親ウィンドウ (GameApp) が存在するか確認
        if self.app:
            # 2. メイン画面の表示を更新 (update_after_battle を実行)
            # 戦闘中に Character オブジェクトの数値（HPやEXP）は既に書き換わっているため、
            # メイン画面の Listbox などを再描画するだけで最新状態になります。
            if hasattr(self.app, "update_after_battle"):
                self.app.update_after_battle()
                print("DEBUG: メイン画面のUIを更新しました。")

        # 3. データの永続化 (セーブ実行)
        # レベルアップしたステータスを即座にファイルに書き出します。
            if hasattr(self.app, "save_game"):
                self.app.save_game()
                print("DEBUG: 戦闘結果をセーブデータに保存しました。")

    # 4. 戦闘ウィンドウ（自分自身）を破棄
    # これにより Toplevel ウィンドウが消え、背後のメイン画面が操作可能になります。
        self.destroy()
    def show_defeat_result(self):
        """敗北画面の表示"""
        defeat_win = tk.Toplevel(self)
        defeat_win.title("GAME OVER")
        defeat_win.geometry("300x250")
        defeat_win.configure(bg="black")

        tk.Label(defeat_win, text="💀 TOTAL DEFEAT 💀", font=("bold", 18), fg="red", bg="black").pack(pady=20)
        tk.Label(defeat_win, text="パーティーは全滅した...", fg="white", bg="black").pack()

        def restart():
            # 全滅からの復帰：HPを1で全員復活させるなどの処置
            for p in self.party:
                p.hp = 1
            defeat_win.destroy()
            self.destroy()

        tk.Button(defeat_win, text="命からがら逃げ出す", command=restart).pack(pady=30)

    def open_switch(self):
        sw = tk.Toplevel(self)
        for m in self.party:
            state = "normal" if m.is_alive() and m != self.current_hero else "disabled"
            tk.Button(sw, text=f"{m.name}(HP:{m.hp})", command=lambda char=m: self.switch_to(char, sw)).pack(pady=2)

    def switch_to(self, char, win):
        self.current_hero = char
        win.destroy()
        self.refresh_buttons()
        self.add_log(f"--- {char.name} が参戦！ ---")
        self.update_ui()
        self.after(600, self.enemies_turn)

# --- 3. メイン管理画面：セーブ＆ロード統合 ---

class GameApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Gemini RPG Editor Pro")
        self.root.geometry("850x700")
        self.save_file = "save_data.json"
        
        self.party = []
        self.enemies = []

        self.setup_ui()
        
        self.load_game() # 起動時に読み込み
        self.update_after_battle()

    def setup_ui(self):
        # JSON入力
        tk.Label(self.root, text="Gemini JSON Input", font=("bold", 10)).pack(pady=5)
        self.input_area = tk.Text(self.root, height=8, width=90)
        self.input_area.pack()

        # 登録ボタン
        btn_f = tk.Frame(self.root)
        btn_f.pack(pady=10)
        tk.Button(btn_f, text="味方登録", bg="#d0f0ff", command=lambda: self.register("player")).pack(side="left", padx=10)
        tk.Button(btn_f, text="敵登録", bg="#ffd0d0", command=lambda: self.register("enemy")).pack(side="left", padx=10)

        # リスト表示
        list_f = tk.Frame(self.root)
        list_f.pack(fill="both", expand=True, padx=20)
        
        # 味方側
        p_frame = tk.LabelFrame(list_f, text=" 味方パーティー (ダブルクリックで詳細) ")
        p_frame.pack(side="left", padx=20, fill="both", expand=True)
        self.p_list = tk.Listbox(p_frame,selectmode='multiple', exportselection=0)
        self.p_list.pack(fill="both", expand=True, padx=5, pady=5)
        self.p_list.bind('<Double-1>', lambda e: self.show_info("player"))

        # 敵側
        e_frame = tk.LabelFrame(list_f, text=" 出現モンスター (ダブルクリックで詳細) ")
        e_frame.pack(side="left", padx=20, fill="both", expand=True)
        self.e_list = tk.Listbox(e_frame,selectmode='multiple', exportselection=0)
        self.e_list.pack(fill="both", expand=True, padx=5, pady=5)
        self.e_list.bind('<Double-1>', lambda e: self.show_info("enemy"))
# ヘルプメッセージ
        tk.Label(self.root, text="※クリックで複数選択できます", fg="gray").pack()
        # 戦闘開始ボタン
        tk.Button(self.root, text="選んだ敵たちとバトル開始！", font=("bold", 14), 
                  bg="#ffcc99", command=self.start_multi_battle).pack(pady=20)
    
    def update_after_battle(self):
        """戦闘から戻ってきた時にメイン画面のパーティーリストを最新の状態にする"""
        
        # 1. リストボックスをクリア（古い情報を消去）
        self.p_list.delete(0, tk.END)
        
        # 2. 最新のパーティーデータをループで回して追加
        for char in self.party:
            # 生死状態のアイコン
            status_icon = "👤" if char.is_alive() else "💀"
            
            # 次のレベルまでの必要経験値を算出（Characterクラスの式に合わせる）
            next_exp_threshold = char.level * 100
            needed_exp = next_exp_threshold - char.exp
            
            # リストに表示する文字列の組み立て
            # 例: [Lv.3] 👤 勇者アルス (HP: 120/120, MP: 45/45) Next: 25exp
            display_text = (
                f"[Lv.{char.level}] {status_icon} {char.name} "
                f"(HP: {char.hp}/{char.max_hp}, MP: {char.mp}/{char.max_mp}) "
                f"あと {needed_exp} exp"
            )
            self.p_list.insert(tk.END, display_text)
            self.p_list.itemconfig(tk.END, fg="green")

            # 3. 視覚的なフィードバック（オプション）
            # HPが低いキャラを赤文字にするなどの工夫も可能（Listboxの仕様上、行ごとの色分けは工夫が必要）
            if not char.is_alive():
                self.p_list.itemconfig(tk.END, fg="red")

        print("システム: メイン画面のステータス表示を同期しました。")
    
    def save_game(self):
        """現在の全キャラクターの状態（成長記録を含む）をJSONに保存"""
        try:
            # 1. 保存用データの組み立て
            save_data = {
                "party": [c.to_dict() for c in self.party],
                "enemies": [c.to_dict() for c in self.enemies]
            }

            # 2. ファイルへの書き出し
            with open(self.save_file, "w", encoding="utf-8") as f:
                # indent=4 で人間が読める形式に、ensure_ascii=False で日本語をそのまま保存
                json.dump(save_data, f, indent=4, ensure_ascii=False)
            
            print("セーブ完了: レベルと経験値が保存されました。")
            
        except Exception as e:
            messagebox.showerror("セーブ失敗", f"データの保存中にエラーが発生しました:\n{e}")

    def load_game(self):
        """保存されたJSONからデータを読み込み、オブジェクトとして復元する"""
        if not os.path.exists(self.save_file):
            print("セーブデータが見つかりません。新規作成します。")
            return

        try:
            with open(self.save_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            # 1. 味方パーティーの復元
            self.party = []
            for d in data.get("party", []):
                # 辞書の中身を Character クラスの引数に展開 (**d)
                char = Character(**d)
                self.party.append(char)

                

            # 2. 敵リスト（図鑑）の復元
            self.enemies = []
            for d in data.get("enemies", []):
                char = Character(**d)
                self.enemies.append(char)
                self.e_list.insert(tk.END, char.name)

            # 3. 画面表示の更新
            self.update_after_battle() 
            print(f"ロード完了: {len(self.party)}人の仲間を読み込みました。")

        except Exception as e:
            messagebox.showerror("ロード失敗", f"データの読み込み中にエラーが発生しました:\n{e}")

    def register(self, side):
        try:
            data = json.loads(self.input_area.get("1.0", tk.END))
            char = Character(**data)
            if side == "player":
                self.party.append(char)
                self.update_after_battle()
            else:
                self.enemies.append(char)
                self.e_list.insert(tk.END, char.name)
            self.save_game() # 登録のたびにセーブ
            self.input_area.delete("1.0", tk.END)
        except Exception as e: messagebox.showerror("Error", e)
    def show_info(self, side):
        if side == "player":
            idx = self.p_list.curselection()
            if idx: DetailWindow(self.root, self.party[idx[0]], "#e0f0ff")
        else:
            idx = self.e_list.curselection()
            if idx: DetailWindow(self.root, self.enemies[idx[0]], "#ffe0e0")

    def start_multi_battle(self):
        p_idx = self.p_list.curselection()
        e_idx = self.e_list.curselection()
        if not p_idx:
            return messagebox.showwarning("警告", "味方を登録してください")
        if not e_idx:
            return messagebox.showwarning("警告", "戦う敵を1体以上選んでください")

        # 選択された敵のデータをリストにまとめる
        current_hero = [self.party[i] for i in p_idx]  # 最初の選択を出撃キャラにする
        selected_enemies = [self.enemies[i] for i in e_idx]

        # 戦闘ウィンドウにリストを渡す
        BattleWindow(self, current_hero, selected_enemies)

        


if __name__ == "__main__":
    GameApp().root.mainloop()