"""System prompts — solo contexto del usuario.
El prompt base (nombre, reglas, herramientas) vive en el Modelfile de Ollama.
"""

from typing import Any


def build_system_prompt(user_context: dict[str, Any] | None = None) -> str:
    """Construye solo el contexto del usuario para complementar el Modelfile de Ollama.

    El Modelfile ya tiene: nombre Claudia, reglas, herramientas.
    Aquí solo agregamos: quién es el usuario, su rol, su empresa, su clienteId.
    """
    ctx = user_context or {}

    if not ctx:
        return ""

    lines: list[str] = []

    if ctx.get("user_name"):
        lines.append(f"Nombre: {ctx['user_name']}")
    if ctx.get("user_username"):
        lines.append(f"Usuario: {ctx['user_username']}")
    if ctx.get("user_rol_nombre"):
        lines.append(f"Rol: {ctx['user_rol_nombre']}")
    if ctx.get("user_telefono"):
        lines.append(f"Teléfono: {ctx['user_telefono']}")
    if ctx.get("user_estatus"):
        lines.append(f"Cuenta: {ctx['user_estatus']}")
    if ctx.get("user_ultimo_login"):
        lines.append(f"Último login: {ctx['user_ultimo_login']}")
    if ctx.get("client_name"):
        lines.append(f"Empresa: {ctx['client_name']}")
    if ctx.get("client_rfc"):
        lines.append(f"RFC: {ctx['client_rfc']}")

    if not lines:
        return ""

    prompt = "USUARIO ACTUAL:\n" + "\n".join(lines)
    prompt += "\nSi pregunta por sus datos personales, responde directo con lo de arriba."

    if ctx.get("client_id"):
        cid = ctx["client_id"]
        prompt += (
            f"\n\nEl clienteId de este usuario es {cid}."
            f" Para sus inmuebles usa idArrendador={cid}."
            f" Para sus arrendatarios usa idArrendador={cid}."
            f" Para sus clientes usa id={cid}."
            f" NUNCA le pidas el ID."
        )

    return prompt


SYSTEM_PROMPT_NO_TOOLS = ""
