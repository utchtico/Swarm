import secrets
import string

from flask import current_app, render_template_string
from flask_mail import Mail, Message

mail = Mail()

# ── Generador de contraseñas temporales ─────────────────────────────────────
_ALFABETO = string.ascii_letters + string.digits + '!@#$%^&*'

def generar_password_temporal(longitud: int = 12) -> str:
    """Genera una contraseña temporal criptográficamente segura."""
    while True:
        pwd = ''.join(secrets.choice(_ALFABETO) for _ in range(longitud))
        # Garantizar al menos un dígito, una mayúscula y un símbolo
        if (any(c.isdigit() for c in pwd) and
                any(c.isupper() for c in pwd) and
                any(c in '!@#$%^&*' for c in pwd)):
            return pwd


# ── Template HTML del correo de invitación ───────────────────────────────────
# Se sustituirá por el template definitivo cuando el usuario lo entregue.
_TEMPLATE_INVITACION = """<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
</head>
<body style="margin:0;padding:0;background:#f6f7fb;font-family:'Segoe UI',Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0">
    <tr><td align="center" style="padding:40px 0;">
      <table width="480" cellpadding="0" cellspacing="0"
             style="background:#fff;border-radius:12px;box-shadow:0 2px 16px rgba(20,40,70,.09);">
        <tr>
          <td style="background:#334155;border-radius:12px 12px 0 0;padding:28px 36px;">
            <h1 style="margin:0;color:#fff;font-size:20px;font-weight:600;">
              Swarm &mdash; UACJ
            </h1>
            <p style="margin:4px 0 0;color:#94a3b8;font-size:13px;">
              Plataforma de optimización por enjambre
            </p>
          </td>
        </tr>
        <tr>
          <td style="padding:32px 36px;">
            <p style="margin:0 0 16px;color:#374151;font-size:15px;">
              Hola <strong>{{ username }}</strong>,
            </p>
            <p style="margin:0 0 24px;color:#6b7280;font-size:14px;line-height:1.6;">
              Has sido invitado a la plataforma <strong>Swarm &mdash; UACJ</strong>.
              A continuación encontrarás tus credenciales de acceso inicial.
              Por seguridad, deberás cambiar tu contraseña al iniciar sesión por primera vez.
            </p>

            <table width="100%" cellpadding="0" cellspacing="0"
                   style="background:#f8fafc;border-radius:8px;border:1px solid #e2e8f0;margin-bottom:24px;">
              <tr>
                <td style="padding:16px 20px;">
                  <p style="margin:0 0 8px;font-size:12px;text-transform:uppercase;
                             letter-spacing:.05em;color:#94a3b8;font-weight:600;">
                    Credenciales
                  </p>
                  <p style="margin:0 0 4px;color:#374151;font-size:14px;">
                    <strong>Usuario:</strong>&nbsp; {{ username }}
                  </p>
                  <p style="margin:0;color:#374151;font-size:14px;">
                    <strong>Contraseña temporal:</strong>&nbsp;
                    <code style="background:#e2e8f0;padding:2px 6px;border-radius:4px;
                                 font-size:13px;letter-spacing:.04em;">{{ password }}</code>
                  </p>
                </td>
              </tr>
            </table>

            <a href="{{ url }}"
               style="display:inline-block;background:#334155;color:#fff;
                      text-decoration:none;padding:12px 28px;border-radius:8px;
                      font-size:14px;font-weight:600;">
              Iniciar sesión &rarr;
            </a>

            <p style="margin:24px 0 0;color:#9ca3af;font-size:12px;line-height:1.5;">
              Si no esperabas esta invitación, puedes ignorar este correo.
              Este mensaje fue generado automáticamente por la plataforma Swarm &mdash; UACJ.
            </p>
          </td>
        </tr>
        <tr>
          <td style="padding:16px 36px;border-top:1px solid #f1f5f9;">
            <p style="margin:0;color:#d1d5db;font-size:11px;">
              Universidad Autónoma de Ciudad Juárez &bull; utch.tico@gmail.com
            </p>
          </td>
        </tr>
      </table>
    </td></tr>
  </table>
</body>
</html>"""


def enviar_invitacion(email: str, username: str, password_temporal: str,
                      url_login: str) -> bool:
    """
    Envía el correo de invitación con las credenciales temporales.
    Retorna True si el envío fue exitoso, False si falló.
    """
    try:
        cuerpo_html = render_template_string(
            _TEMPLATE_INVITACION,
            username=username,
            password=password_temporal,
            url=url_login,
        )
        msg = Message(
            subject='Invitación a Swarm — UACJ',
            recipients=[email],
            html=cuerpo_html,
        )
        mail.send(msg)
        return True
    except Exception as exc:
        current_app.logger.error(f'[email] Error al enviar invitación a {email}: {exc}')
        return False


def enviar_reset_password(email: str, username: str,
                          password_temporal: str, url_login: str) -> bool:
    """Envía un correo de reseteo de contraseña (mismo template, asunto diferente)."""
    try:
        cuerpo_html = render_template_string(
            _TEMPLATE_INVITACION,
            username=username,
            password=password_temporal,
            url=url_login,
        )
        msg = Message(
            subject='Restablecimiento de contraseña — Swarm UACJ',
            recipients=[email],
            html=cuerpo_html,
        )
        mail.send(msg)
        return True
    except Exception as exc:
        current_app.logger.error(f'[email] Error al enviar reset a {email}: {exc}')
        return False