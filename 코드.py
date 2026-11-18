import tkinter as tk
from tkinter import messagebox
import random
import winsound

class ClickGameApp:
    def __init__(self, root):
        self.root = root
        self.root.title("클릭 서바이벌")
        self.root.geometry("900x600")
        self.root.resizable(False, False)
        
        self.db_connect()
        self.show_main_screen()

    def db_connect(self):
        try:
            self.conn = mysql.connector.connect(
                host="localhost",
                user="root",
                password="1234",
                database="click_game_db"
            )
            self.cursor = self.conn.cursor()
        except Exception as e:
            print(f"DB 연결 실패 (오프라인 모드): {e}")
            self.conn = None
            self.cursor = None

    def show_main_screen(self):
        for widget in self.root.winfo_children():
            widget.destroy()

        main_frame = tk.Frame(self.root, bg="#2c3e50")
        main_frame.pack(fill="both", expand=True)

        title_lbl = tk.Label(main_frame, text="🎯 원 클릭 서바이벌", font=("Arial", 30, "bold"), bg="#2c3e50", fg="white")
        title_lbl.pack(pady=100)

        start_btn = tk.Button(main_frame, text="게임 시작", font=("Arial", 16, "bold"), width=15, height=2, bg="#2ecc71", fg="white", command=self.start_game)
        start_btn.pack(pady=20)

        exit_btn = tk.Button(main_frame, text="게임 종료", font=("Arial", 16, "bold"), width=15, height=2, bg="#e74c3c", fg="white", command=self.root.quit)
        exit_btn.pack(pady=10)

    def start_game(self):
        for widget in self.root.winfo_children():
            widget.destroy()

        self.score = 0
        self.life = 5
        self.is_penalized = False 
        
        self.circles = {}
        self.loop_id = None
        self.spawn_counter = 0  
        
        self.left_canvas = tk.Canvas(self.root, width=600, height=600, bg="white")
        self.left_canvas.pack(side="left", fill="both")
        self.left_canvas.bind("<Button-1>", self.on_canvas_click)

        right_frame = tk.Frame(self.root, width=300, height=600, bg="#ecf0f1")
        right_frame.pack(side="right", fill="both", expand=True)

        score_panel = tk.Frame(right_frame, bg="#bdc3c7", height=200)
        score_panel.pack(fill="x", padx=10, pady=10)
        
        self.score_lbl = tk.Label(score_panel, text=f"점수: {self.score}", font=("Arial", 16, "bold"), bg="#bdc3c7")
        self.score_lbl.pack(pady=20)
        
        self.life_lbl = tk.Label(score_panel, text=f"라이프: {'❤️' * self.life} ({self.life})", font=("Arial", 14), bg="#bdc3c7", fg="#c0392b")
        self.life_lbl.pack(pady=10)

        rank_panel = tk.Frame(right_frame, bg="white", relief="solid", bd=1)
        rank_panel.pack(fill="both", expand=True, padx=10, pady=10)

        tk.Label(rank_panel, text="🏆 TOP 10 랭킹", font=("Arial", 14, "bold"), bg="white").pack(pady=10)
        
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
            self.cursor.execute("SELECT nickname, score FROM ranking ORDER BY score DESC, created_at ASC LIMIT 10;")
            rows = self.cursor.fetchall()
            for idx, (nick, scr) in enumerate(rows, 1):
                self.rank_listbox.insert(tk.END, f"{idx}위 : {nick} ({scr}점)")
        except Exception as e:
            self.rank_listbox.insert(tk.END, "랭킹 불러오기 실패")

    def spawn_circle(self):
        if len(self.circles) >= 3:
            return

        r = 65
        x = random.randint(r + 10, 600 - r - 10)
        y = random.randint(r + 10, 600 - r - 10)
        
        oval_id = self.left_canvas.create_oval(
            x - r, y - r, x + r, y + r, 
            fill="#3498db", outline="#2980b9", width=2
        )
        
        self.circles[oval_id] = {'x': x, 'y': y, 'r': r}

    def run_game_loop(self):
        speed_delay = max(15, 22 - (self.score // 150) * 1)
        spawn_threshold = max(20, 35 - (self.score // 100) * 3)
        
        self.spawn_counter += 1
        if self.spawn_counter >= spawn_threshold:
            self.spawn_circle()
            self.spawn_counter = 0

        expired_circles = []
        for oval_id, data in list(self.circles.items()):
            data['r'] -= 1  
            if data['r'] > 2:
                x, y, r = data['x'], data['y'], data['r']
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
        if self.is_penalized:
            return  
        
        hit_any = False
        for oval_id, data in list(self.circles.items()):
            distance = ((event.x - data['x']) ** 2 + (event.y - data['y']) ** 2) ** 0.5
            if distance <= data['r']:
                hit_any = True
                self.left_canvas.delete(oval_id)
                del self.circles[oval_id]
                
                # [수정] 성공 효과음: 주파수를 낮추고(550Hz) 지속 시간을 짧게(25ms) 줄여 부드러운 '톡' 소리로 변경
                try:
                    winsound.Beep(550, 25)
                except:
                    pass

                self.score += 10
                self.score_lbl.config(text=f"점수: {self.score}")
                break  
        
        if not hit_any:
            try:
                winsound.Beep(300, 50)
            except:
                pass

            self.is_penalized = True
            self.left_canvas.config(bg="#fadbd8")
            self.root.after(300, self.remove_penalty)

    def remove_penalty(self):
        self.is_penalized = False
        self.left_canvas.config(bg="white")

    def lose_life(self):
        try:
            winsound.Beep(200, 100)
        except:
            pass

        self.life -= 1
        self.life_lbl.config(text=f"라이프: {'❤️' * self.life} ({self.life})")
        
        if self.life <= 0:
            if self.loop_id:
                self.root.after_cancel(self.loop_id)
            messagebox.showinfo("게임 종료", f"게임 오버! 최종 점수: {self.score}점")
            self.show_main_screen()

if __name__ == "__main__":
    root = tk.Tk()
    app = ClickGameApp(root)
    root.mainloop()