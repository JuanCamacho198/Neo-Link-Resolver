from nicegui import ui

@ui.page('/')
def main():
    ui.label('Si puedes ver esto, NiceGUI funciona correctamente.').classes('text-h4 p-8')
    ui.button('Probar botón', on_click=lambda: ui.notify('¡Funciona!'))

if __name__ in {"__main__", "__mp_main__"}:
    ui.run(port=8084, title='Test Minimal', reload=False)
