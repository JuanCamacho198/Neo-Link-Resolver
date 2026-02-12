import tkinter as tk
from tkinter import messagebox

def on_click():
    messagebox.showinfo("Neo-Link-Resolver", "¡La interfaz de escritorio funciona!")

root = tk.Tk()
root.title("Test Escritorio")
root.geometry("300x200")

label = tk.Label(root, text="Si ves esta ventana,\nla versión de escritorio funcionará.", padx=20, pady=20)
label.pack()

btn = tk.Button(root, text="Probar Click", command=on_click)
btn.pack(pady=10)

root.mainloop()
