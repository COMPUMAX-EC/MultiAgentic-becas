"""
MultiAgentic-Becas — Entry Point
Arranca el backend FastAPI o el frontend Streamlit según argumentos.
"""
import sys
import uvicorn


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "api"

    if mode == "api":
        print("🚀 Iniciando MultiAgentic-Becas API en http://localhost:8080")
        print("📖 Documentación: http://localhost:8080/docs")
        uvicorn.run(
            "api.main:app",
            host="0.0.0.0",
            port=8080,
            reload=True,
            log_level="info",
        )

    elif mode == "ui":
        import subprocess
        print("🎓 Iniciando frontend Streamlit en http://localhost:8501")
        subprocess.run([
            sys.executable, "-m", "streamlit", "run",
            "frontend/app.py",
            "--server.port", "8501",
            "--server.address", "0.0.0.0",
        ])

    else:
        print(f"Modo desconocido: '{mode}'. Usa 'api' o 'ui'.")
        sys.exit(1)


if __name__ == "__main__":
    main()
