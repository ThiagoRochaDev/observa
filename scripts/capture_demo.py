from __future__ import annotations

import os
import subprocess
import sys
from html import escape
from pathlib import Path

from playwright.sync_api import Page, sync_playwright


ROOT = Path(__file__).resolve().parents[1]
FRAMES = ROOT / "docs" / "demo" / "frames"
BASE_URL = os.getenv("OBSERVA_DEMO_URL", "http://localhost:3000")
EDGE = Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")


def title_frame(page: Page, filename: str, eyebrow: str, title: str, body: str) -> None:
    page.set_content(
        f"""
        <!doctype html><html><head><meta charset="utf-8"><style>
        * {{ box-sizing: border-box }}
        body {{ margin: 0; width: 1440px; height: 900px; display: grid; place-items: center;
          background: radial-gradient(circle at 20% 10%, #173f5f 0, #08131f 45%, #03070c 100%);
          color: #f3f8fb; font-family: Inter, ui-sans-serif, system-ui, sans-serif; }}
        main {{ width: 1040px; padding: 72px; border: 1px solid #31536b; border-radius: 28px;
          background: rgba(7, 18, 29, .9); box-shadow: 0 32px 80px #0008; }}
        .eyebrow {{ color: #68d9c0; letter-spacing: .16em; text-transform: uppercase; font-weight: 800; }}
        h1 {{ margin: 18px 0; font-size: 68px; line-height: 1.05; }}
        p {{ margin: 0; max-width: 850px; color: #adc2d1; font-size: 28px; line-height: 1.45; }}
        .pill {{ display: inline-block; margin-top: 36px; padding: 12px 20px; border-radius: 999px;
          background: #123a45; color: #8ff3dc; font-size: 18px; font-weight: 700; }}
        </style></head><body><main><div class="eyebrow">{eyebrow}</div><h1>{title}</h1>
        <p>{body}</p><div class="pill">Observa · FinOps, governança e confiabilidade</div></main></body></html>
        """
    )
    page.screenshot(path=FRAMES / filename)


def capture_page(page: Page, filename: str, path: str) -> None:
    page.goto(f"{BASE_URL}{path}", wait_until="networkidle")
    page.wait_for_timeout(900)
    page.screenshot(path=FRAMES / filename)


def cli_frame(page: Page) -> None:
    environment = os.environ.copy()
    environment["OBSERVA_URL"] = os.getenv("OBSERVA_API_URL", "http://127.0.0.1:8080")
    environment["OBSERVA_API_KEY"] = os.environ["OBSERVA_DEMO_API_KEY"]
    commands = [
        (["companies", "list"], "observa companies list"),
        (["resources", "--untagged"], "observa resources --untagged"),
        (["budgets", "list"], "observa budgets list"),
    ]
    chunks: list[str] = []
    for arguments, label in commands:
        result = subprocess.run(
            [sys.executable, "-m", "observa_cli.main", *arguments],
            cwd=ROOT / "apps" / "cli",
            env=environment,
            capture_output=True,
            text=True,
            check=True,
        )
        chunks.append(f"> {label}\n{result.stdout.strip()}")
    output = "\n\n".join(chunks)
    page.set_content(
        f"""<!doctype html><html><head><meta charset="utf-8"><style>
        body {{ margin:0; background:#080b10; color:#d7e2ef; font:20px Consolas,monospace; padding:48px }}
        h1 {{ color:#59d9b5; font:800 38px Arial }}
        pre {{ white-space:pre-wrap; background:#121821; border:1px solid #263244; border-radius:14px;
          padding:28px; line-height:1.55 }}
        </style></head><body><h1>Observa CLI · multi-tenancy</h1><pre>{escape(output)}</pre></body></html>"""
    )
    page.screenshot(path=FRAMES / "110-cli.png")


def mobile_frame(page: Page) -> None:
    page.set_content(
        """<!doctype html><html><head><meta charset="utf-8"><style>
        body{margin:0;background:#080b10;color:#f5f7fa;font-family:Arial;display:grid;place-items:center;height:100vh}
        .phone{width:390px;height:760px;border:12px solid #222b38;border-radius:42px;background:#080b10;padding:30px 22px;box-shadow:0 30px 80px #000}
        .brand{font-size:34px;font-weight:800}.sub{color:#94a3b8;margin:5px 0 4px}.ctx{color:#59d9b5;font-size:12px;margin-bottom:25px}
        .metrics{display:flex;gap:8px}.card{background:#121821;border:1px solid #263244;border-radius:12px;padding:14px;margin:10px 0}.metric{flex:1}
        .val{color:#59d9b5;font-size:18px;font-weight:800}.label{color:#94a3b8;font-size:12px}h2{font-size:19px;margin-top:26px}
        .btn{display:inline-block;background:#59d9b5;color:#07110e;border-radius:8px;padding:9px 12px;font-weight:800;margin:10px 5px 0 0}
        .danger{background:transparent;color:#f87171;border:1px solid #f87171}
        </style></head><body><div class="phone"><div class="brand">Observa</div><div class="sub">Custos, recursos e aprovações</div>
        <div class="ctx">Example Corp · Produção</div><div class="metrics"><div class="card metric"><div class="val">R$ 15.523</div>
        <div class="label">Custo 30 dias</div></div><div class="card metric"><div class="val">6</div><div class="label">Alertas</div></div></div>
        <h2>Aprovações pendentes</h2><div class="card"><b>Governança approval-first</b><div class="label">0 ações aguardando decisão</div></div>
        <h2>Remediações sugeridas</h2><div class="card"><b>Falha da aplicação · storefront/api</b><div class="label">Correção sugerida localmente,
        com execução somente após aprovação.</div><span class="btn">Aprovar dry-run</span><span class="btn danger">Rejeitar</span></div></div></body></html>"""
    )
    page.screenshot(path=FRAMES / "120-mobile.png")


def main() -> None:
    api_key = os.environ["OBSERVA_DEMO_API_KEY"]
    if not EDGE.exists():
        raise RuntimeError(f"Microsoft Edge not found at {EDGE}")

    FRAMES.mkdir(parents=True, exist_ok=True)
    for old_frame in FRAMES.glob("*.png"):
        old_frame.unlink()

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True, executable_path=str(EDGE))
        page = browser.new_page(viewport={"width": 1440, "height": 900}, device_scale_factor=1)

        title_frame(
            page,
            "001-title.png",
            "Demonstração completa",
            "Observa",
            "Plataforma multiempresa para custos, recursos, budgets, logs, aprovações e remediação segura.",
        )

        page.goto(BASE_URL, wait_until="domcontentloaded")
        page.evaluate("key => localStorage.setItem('observa_api_key', key)", api_key)
        page.evaluate("localStorage.setItem('observa_company_id', 'cmp_default')")
        page.evaluate("localStorage.setItem('observa_tenancy_id', 'tnt_default')")
        routes = [
            ("010-overview.png", "/"),
            ("020-products.png", "/products"),
            ("030-inventory.png", "/inventory"),
            ("040-budgets.png", "/budgets"),
            ("050-governance.png", "/governance"),
            ("060-connections.png", "/connections"),
            ("070-alerts.png", "/alerts"),
            ("080-dashboards.png", "/dashboards"),
            ("090-observability.png", "/observability"),
            ("100-logs.png", "/logs"),
            ("110-traces.png", "/traces"),
            ("120-monitors.png", "/monitors"),
            ("130-rum.png", "/rum"),
            ("140-gcp.png", "/gcp"),
            ("150-maps.png", "/maps"),
            ("160-remediations.png", "/remediations"),
            ("170-auth.png", "/settings/auth"),
            ("180-organizations.png", "/settings/organizations"),
        ]
        for filename, path in routes:
            capture_page(page, filename, path)

        page.goto(f"{BASE_URL}/", wait_until="networkidle")
        search = page.get_by_placeholder("Qual serviço você deseja acessar?")
        search.fill("conexões")
        page.wait_for_timeout(500)
        page.screenshot(path=FRAMES / "015-global-search.png")

        page.goto(f"{BASE_URL}/connections", wait_until="networkidle")
        page.get_by_placeholder("Buscar conectores…").fill("GitHub")
        page.wait_for_timeout(500)
        page.get_by_text("GitHub", exact=True).first.click()
        page.wait_for_timeout(500)
        page.screenshot(path=FRAMES / "065-github-connector.png")

        page.goto(f"{BASE_URL}/dashboards", wait_until="networkidle")
        dashboard = page.locator("a[href^='/dashboards/']").first
        dashboard_href = dashboard.get_attribute("href")
        if dashboard_href:
            capture_page(page, "085-dashboard-detail.png", dashboard_href)

        page.goto(f"{BASE_URL}/products", wait_until="networkidle")
        product = page.locator("a[href^='/products/']").first
        product_href = product.get_attribute("href")
        if product_href:
            capture_page(page, "025-product-detail.png", product_href)

        title_frame(
            page,
            "190-automation.png",
            "Segurança por padrão",
            "Aprovar antes de agir",
            "Dry-run, trilha de auditoria, papéis por tenancy e isolamento físico de dados entre empresas.",
        )
        cli_frame(page)
        (FRAMES / "110-cli.png").rename(FRAMES / "200-cli.png")
        mobile_frame(page)
        (FRAMES / "120-mobile.png").rename(FRAMES / "210-mobile.png")
        title_frame(
            page,
            "220-finish.png",
            "Execução portátil",
            "Cloud, Kubernetes, VM ou local",
            "Conectores extensíveis para nuvem, on-premises, GitLab, observabilidade e qualquer ferramenta da empresa.",
        )
        browser.close()

    print(f"Captured {len(list(FRAMES.glob('*.png')))} safe frames in {FRAMES}")


if __name__ == "__main__":
    main()
