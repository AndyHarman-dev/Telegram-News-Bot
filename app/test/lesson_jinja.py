from jinja2 import Template

name = "Art"

tm = Template("Hi {{ name }}")
msg = tm.render(name=name)

print(msg)