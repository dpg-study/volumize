from tkinter import ttk


def setup_styles():
    """Настройка современных стилей"""
    style = ttk.Style()

    # Цветовая схема
    bg_color = '#2b2b2b'
    fg_color = '#ffffff'
    accent_color = '#0078d4'

    style.theme_use('clam')

    style.configure('TLabel', background=bg_color, foreground=fg_color, font=('Segoe UI', 10))
    style.configure('TFrame', background=bg_color)
    style.configure('TLabelframe', background=bg_color, foreground=fg_color, font=('Segoe UI', 10, 'bold'))
    style.configure('TLabelframe.Label', background=bg_color, foreground=fg_color, font=('Segoe UI', 10, 'bold'))

    style.configure('Accent.TButton',
                    background=accent_color,
                    foreground='white',
                    borderwidth=0,
                    font=('Segoe UI', 10))
    style.map('Accent.TButton',
              background=[('active', '#005a9e'), ('pressed', '#004578')])

    style.configure('TButton',
                    background='#404040',
                    foreground='white',
                    borderwidth=1,
                    font=('Segoe UI', 10))
    style.map('TButton',
              background=[('active', '#505050'), ('pressed', '#303030')])

    style.configure('TEntry', fieldbackground='#404040', foreground='white')
    style.configure('Horizontal.TProgressbar',
                    background=accent_color,
                    troughcolor='#404040')