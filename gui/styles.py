from tkinter import ttk


def setup_styles():
    style = ttk.Style()
    style.theme_use('clam')


    BG_MAIN = '#21252B'
    BG_CARD = '#282C34'
    BG_INSET = '#1B1E23'
    ACCENT = '#61AFEF'
    ACCENT_H = '#82BFF3'
    FG_MAIN = '#ABB2BF'
    FG_BRIGHT = '#ECEFF4'
    BORDER = '#181A1F'
    ERROR = '#E06C75'
    SUCCESS = '#98C379'

    style.configure('.', background=BG_MAIN, foreground=FG_MAIN, font=('Segoe UI', 10))

    # Рамки и панели
    style.configure('TFrame', background=BG_MAIN)
    style.configure('Card.TFrame', background=BG_CARD)
    style.configure('TPanedwindow', background=BORDER)

    # Кнопки
    style.configure('TButton', background=BG_CARD, foreground=FG_BRIGHT, borderwidth=0, focuscolor='none',
                    padding=(10, 6))
    style.map('TButton',
              background=[('active', '#353B45'), ('disabled', BG_MAIN)],
              foreground=[('disabled', '#545862')])

    style.configure('Accent.TButton', background=ACCENT, foreground='white', font=('Segoe UI Bold', 10))
    style.map('Accent.TButton', background=[('active', ACCENT_H)])

    style.configure('Stop.TButton', background=BG_CARD, foreground=ERROR, font=('Segoe UI Bold', 10))
    style.map('Stop.TButton', background=[('active', '#3D3133')])

    # Заголовки групп
    style.configure('TLabelframe', background=BG_MAIN, bordercolor=BORDER, borderwidth=1)
    style.configure('TLabelframe.Label', background=BG_MAIN, foreground=ACCENT, font=('Segoe UI Bold', 9))

    # Ввод и Прогресс
    style.configure('TEntry', fieldbackground=BG_INSET, bordercolor=BORDER, lightcolor=BORDER, darkcolor=BORDER,
                    padding=5)
    style.configure('Custom.Horizontal.TProgressbar', thickness=6, troughcolor=BG_INSET, background=ACCENT,
                    bordercolor=BORDER)