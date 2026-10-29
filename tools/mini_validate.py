"""Validator JSON Schema MINIMAL (hanya fitur yang dipakai scad.schema.json). Untuk pemeriksaan cepat tanpa
dependensi. Untuk produksi pakai paket `jsonschema` (Draft202012Validator)."""
import re

def _ref(root, ref):
    node = root
    for part in ref.lstrip("#/").split("/"):
        node = node[part]
    return node

def _is(v, t):
    return {"object": isinstance(v, dict), "array": isinstance(v, list), "string": isinstance(v, str),
            "null": v is None, "boolean": isinstance(v, bool),
            "integer": (isinstance(v, int) and not isinstance(v, bool)) or (isinstance(v, float) and v.is_integer()),
            "number": isinstance(v, (int, float)) and not isinstance(v, bool)}[t]

def validate(inst, schema, root=None, path=""):
    root = root or schema
    errs = []
    if "$ref" in schema:
        return validate(inst, _ref(root, schema["$ref"]), root, path)
    if "type" in schema:
        ts = schema["type"] if isinstance(schema["type"], list) else [schema["type"]]
        if not any(_is(inst, t) for t in ts):
            return [f"{path or '/'}: tipe harus {ts}"]
    if "const" in schema and inst != schema["const"]:
        errs.append(f"{path or '/'}: harus {schema['const']!r}")
    if "enum" in schema and inst not in schema["enum"]:
        errs.append(f"{path or '/'}: harus salah satu dari {schema['enum']}")
    if isinstance(inst, str):
        if "pattern" in schema and not re.search(schema["pattern"], inst):
            errs.append(f"{path or '/'}: tidak cocok pola {schema['pattern']}")
        if "minLength" in schema and len(inst) < schema["minLength"]:
            errs.append(f"{path or '/'}: terlalu pendek")
    if _is(inst, "number") and not isinstance(inst, bool):
        if "minimum" in schema and inst < schema["minimum"]: errs.append(f"{path or '/'}: < {schema['minimum']}")
        if "maximum" in schema and inst > schema["maximum"]: errs.append(f"{path or '/'}: > {schema['maximum']}")
        if "exclusiveMinimum" in schema and inst <= schema["exclusiveMinimum"]: errs.append(f"{path or '/'}: harus > {schema['exclusiveMinimum']}")
    if isinstance(inst, list):
        if "minItems" in schema and len(inst) < schema["minItems"]: errs.append(f"{path or '/'}: kurang dari {schema['minItems']} item")
        if "maxItems" in schema and len(inst) > schema["maxItems"]: errs.append(f"{path or '/'}: lebih dari {schema['maxItems']} item")
        if schema.get("uniqueItems") and len({repr(x) for x in inst}) != len(inst): errs.append(f"{path or '/'}: item harus unik")
        if "items" in schema:
            for i, x in enumerate(inst): errs += validate(x, schema["items"], root, f"{path}/{i}")
    if isinstance(inst, dict):
        for k in schema.get("required", []):
            if k not in inst: errs.append(f"{path or '/'}: kunci wajib '{k}' tidak ada")
        props, pats = schema.get("properties", {}), schema.get("patternProperties", {})
        for k, v in inst.items():
            matched = False
            if k in props:
                matched = True; errs += validate(v, props[k], root, f"{path}/{k}")
            for pat, sub in pats.items():
                if re.search(pat, k):
                    matched = True; errs += validate(v, sub, root, f"{path}/{k}")
            if not matched and "additionalProperties" in schema:
                ap = schema["additionalProperties"]
                if ap is False: errs.append(f"{path}/{k}: kunci tidak dikenal")
                elif isinstance(ap, dict): errs += validate(v, ap, root, f"{path}/{k}")
        if "propertyNames" in schema:
            for k in inst: errs += [f"{path}/{k}: nama kunci tidak valid" for _ in validate(k, schema["propertyNames"], root, "")]
    for sub in schema.get("allOf", []): errs += validate(inst, sub, root, path)
    if "anyOf" in schema and not any(not validate(inst, s, root, path) for s in schema["anyOf"]):
        errs.append(f"{path or '/'}: tidak cocok dengan satu pun varian (anyOf)")
    if "oneOf" in schema:
        n = sum(1 for s in schema["oneOf"] if not validate(inst, s, root, path))
        if n != 1: errs.append(f"{path or '/'}: harus cocok dengan tepat satu varian (cocok dengan {n})")
    if "not" in schema and not validate(inst, schema["not"], root, path):
        errs.append(f"{path or '/'}: melanggar 'not'")
    if "if" in schema:
        if not validate(inst, schema["if"], root, path):
            if "then" in schema: errs += validate(inst, schema["then"], root, path)
        elif "else" in schema: errs += validate(inst, schema["else"], root, path)
    return errs
