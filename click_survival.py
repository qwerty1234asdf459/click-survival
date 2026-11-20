import tkinter as tk
from tkinter import messagebox
import random
import threading
import mysql.connector
import winsound


class ClickGameApp:

  def __init__(self, root):
    self.root = root
    self.root.title("원 클릭 서바이벌")
    self.root.geometry("900x600")
    self.root.resizable(False, False)

    self.loop_id = None
    self.db_connect()
    self.show_main_screen()

  def play_beep(self, freq, duration):
    """UI 루프를 멈추지 않도록 별도 스레드에서 효과음 재생"""
    def _beep():
      try:
        winsound.Beep(freq, duration)
      except Exception:
        pass

    threading.Thread(target=_beep, daemon=True).start()

  def format_life_text(self):
    current_life = max(0, self.life)
    hearts = " ".join(["♥"] * current_life)
    return f"라이프: {hearts} ({current_life})"

  def db_connect(self):
    try:
      self.conn = mysql.connector.connect(
          host="172.16.52.101",
          port=3306,
          user="root",
          password="1234",
          database="click_game_db",
          charset="utf8mb4",
      )
      self.cursor = self.conn.cursor()
    except Exception as e:
      messagebox.showwarning(
          "DB 연결 실패", f"오프라인 모드로 실행됩니다.\n원인: {e}"
      )
      self.conn = None
      self.cursor = None

  def show_main_screen(self):
    if self.loop_id:
      self.root.after_cancel(self.loop_id)
      self.loop_id = None

    for widget in self.root.winfo_children():
      widget.destroy()

    main_frame = tk.Frame(self.root, bg="#2c3e50")
    main_frame.pack(fill="both", expand=True)

    title_lbl = tk.Label(
        main_frame,
        text="🎯 원 클릭 서바이벌",
        font=("Arial", 30, "bold"),
        bg="#2c3e50",
        fg="white",
    )
    title_lbl.pack(pady=100)

    start_btn = tk.Button(
        main_frame,
        text="게임 시작",
        font=("Arial", 16, "bold"),
        width=15,
        height=2,
        bg="#2ecc71",
        fg="white",
        command=self.start_game,
    )
    start_btn.pack(pady=20)

    exit_btn = tk.Button(
        main_frame,
        text="게임 종료",
        font=("Arial", 16, "bold"),
        width=15,
        height=2,
        bg="#e74c3c",
        fg="white",
        command=self.root.quit,
    )
    exit_btn.pack(pady=10)

  def start_game(self):
    if self.loop_id:
      self.root.after_cancel(self.loop_id)
      self.loop_id = None

    for widget in self.root.winfo_children():
      widget.destroy()

    self.score = 0
    self.life = 5
    self.is_penalized = False

    self.circles = {}
    self.spawn_counter = 0

    self.left_canvas = tk.Canvas(self.root, width=600, height=600, bg="white")
    self.left_canvas.pack(side="left", fill="both")
    self.left_canvas.bind("<Button-1>", self.on_canvas_click)

    right_frame = tk.Frame(self.root, width=300, height=600, bg="#ecf0f1")
    right_frame.pack(side="right", fill="both", expand=True)

    score_panel = tk.Frame(right_frame, bg="#bdc3c7", height=200)
    score_panel.pack(fill="x", padx=10, pady=10)

    self.score_lbl = tk.Label(
        score_panel,
        text=f"점수: {self.score}",
        font=("Arial", 16, "bold"),
        bg="#bdc3c7",
    )
    self.score_lbl.pack(pady=20)

    self.life_lbl = tk.Label(
        score_panel,
        text=self.format_life_text(),
        font=("Arial", 14),
        bg="#bdc3c7",
        fg="#c0392b",
        wraplength=260,
        justify="center",
    )
    self.life_lbl.pack(pady=10)

    rank_panel = tk.Frame(right_frame, bg="white", relief="solid", bd=1)
    rank_panel.pack(fill="both", expand=True, padx=10, pady=10)

    tk.Label(
        rank_panel, text="🏆 TOP 10 랭킹", font=("Arial", 14, "bold"), bg="white"
    ).pack(pady=10)

    self.rank_listbox = tk.Listbox(rank_panel, font=("Arial", 11), height=15)
    self.rank_listbox.pack(fill="both", expand=True, padx=10, pady=5)

    self.load_rankings()

    self.spawn_circle()
    self.run_game_loop()

  def load_rankings(self):
    self.rank_listbox.delete(0, tk.END)
    if not self.cursor:
      self.rank_listbox.insert(tk.END, "DB 미연동 상태")
      return
    try:
      self.cursor.execute(
          "SELECT nickname, score FROM ranking ORDER BY score DESC, created_at"
          " ASC LIMIT 10;"
      )
      rows = self.cursor.fetchall()
      for idx, (nick, scr) in enumerate(rows, 1):
        self.rank_listbox.insert(tk.END, f"{idx}위 : {nick} ({scr}점)")
    except Exception as e:
      self.rank_listbox.insert(tk.END, f"랭킹 불러오기 실패: {e}")

  def spawn_circle(self):
    if len(self.circles) >= 3:
      return

    r = 65
    x = random.randint(r + 10, 600 - r - 10)
    y = random.randint(r + 10, 600 - r - 10)

    oval_id = self.left_canvas.create_oval(
        x - r, y - r, x + r, y + r, fill="#3498db", outline="#2980b9", width=2
    )

    self.circles[oval_id] = {"x": x, "y": y, "r": r}

  def run_game_loop(self):
    if self.life <= 0:
      return

    speed_delay = max(15, 22 - (self.score // 150) * 1)
    spawn_threshold = max(20, 35 - (self.score // 100) * 3)

    self.spawn_counter += 1
    if self.spawn_counter >= spawn_threshold:
      self.spawn_circle()
      self.spawn_counter = 0

    expired_circles = []
    for oval_id, data in list(self.circles.items()):
      data["r"] -= 1
      if data["r"] > 2:
        x, y, r = data["x"], data["y"], data["r"]
        self.left_canvas.coords(oval_id, x - r, y - r, x + r, y + r)
      else:
        expired_circles.append(oval_id)

    for oval_id in expired_circles:
      self.left_canvas.delete(oval_id)
      del self.circles[oval_id]
      self.lose_life()
      if self.life <= 0:
        return

    self.loop_id = self.root.after(speed_delay, self.run_game_loop)

  def on_canvas_click(self, event):
    if self.is_penalized or self.life <= 0:
      return

    hit_any = False
    for oval_id, data in list(self.circles.items()):
      distance = ((event.x - data["x"]) ** 2 + (event.y - data["y"]) ** 2) ** 0.5
      if distance <= data["r"]:
        hit_any = True
        self.left_canvas.delete(oval_id)
        del self.circles[oval_id]

        self.play_beep(550, 25)

        self.score += 10
        self.score_lbl.config(text=f"점수: {self.score}")
        break

    if not hit_any:
      self.play_beep(300, 50)

      self.is_penalized = True
      self.left_canvas.config(bg="#fadbd8")
      self.root.after(300, self.remove_penalty)

  def remove_penalty(self):
    self.is_penalized = False
    if self.life > 0:
      try:
        self.left_canvas.config(bg="white")
      except tk.TclError:
        pass

  def lose_life(self):
    self.play_beep(200, 100)

    self.life -= 1
    self.life_lbl.config(text=self.format_life_text())

    if self.life <= 0:
      if self.loop_id:
        self.root.after_cancel(self.loop_id)
        self.loop_id = None

      if not self.conn or not self.cursor:
        messagebox.showinfo(
            "게임 오버",
            f"최종 점수: {self.score}점\nDB 미연동 상태라 메인화면으로 돌아갑니다.",
        )
        self.show_main_screen()
      else:
        self.open_nickname_modal()

  def open_nickname_modal(self):
    """게임 오버 시 닉네임을 입력받아 ranking 테이블에 저장하는 모달 창"""
    modal = tk.Toplevel(self.root)
    modal.title("게임 오버 - 기록 등록")
    modal.geometry("360x200")
    modal.resizable(False, False)
    modal.transient(self.root)
    modal.grab_set()

    # 창 닫기(X) 버튼 방지: 닉네임 입력 후 확인을 누르도록 유도
    modal.protocol("WM_DELETE_WINDOW", lambda: None)

    tk.Label(
        modal,
        text=f"최종 점수: {self.score}점",
        font=("Arial", 14, "bold"),
        fg="#2c3e50",
    ).pack(pady=(18, 6))

    tk.Label(
        modal, text="랭킹에 등록할 닉네임을 입력하세요:", font=("Arial", 11)
    ).pack()

    entry = tk.Entry(modal, font=("Arial", 12), width=22, justify="center")
    entry.pack(pady=10)
    entry.focus_set()

    def submit_nickname(event=None):
      nickname = entry.get().strip()
      if not nickname:
        messagebox.showwarning(
            "입력 필요",
            "닉네임을 입력하지 않았습니다.\n닉네임을 다시 입력해주세요.",
            parent=modal,
        )
        entry.focus_set()
        return

      if not self.conn or not self.cursor:
        messagebox.showinfo(
            "게임 오버",
            "DB 미연동 상태라 메인화면으로 돌아갑니다.",
            parent=modal,
        )
        modal.destroy()
        self.show_main_screen()
        return

      try:
        query = "INSERT INTO ranking (nickname, score) VALUES (%s, %s)"
        self.cursor.execute(query, (nickname, self.score))
        self.conn.commit()
        messagebox.showinfo(
            "등록 완료",
            f"'{nickname}' 님의 {self.score}점 기록이 저장되었습니다!",
            parent=modal,
        )
        modal.destroy()
        self.show_main_screen()
      except Exception as e:
        messagebox.showerror(
            "저장 실패", f"랭킹 저장 중 오류가 발생했습니다:\n{e}", parent=modal
        )

    entry.bind("<Return>", submit_nickname)

    btn_frame = tk.Frame(modal)
    btn_frame.pack(pady=8)

    tk.Button(
        btn_frame,
        text="확인",
        font=("Arial", 11, "bold"),
        width=10,
        bg="#3498db",
        fg="white",
        command=submit_nickname,
    ).pack(side="left", padx=6)

    self.root.wait_window(modal)


if __name__ == "__main__":
  root = tk.Tk()
  app = ClickGameApp(root)
  root.mainloop()