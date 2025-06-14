import base64
import dataclasses
import functools
import math
import os
import pathlib
import re
import collections.abc

import cyclopts


infill_pattern = r'<[A-Z_]+(?:_[0-9]+)?>'
infill_matcher = re.compile(infill_pattern)
random_infill_pattern = '<GENERATE_RANDOM_([0-9]+)>'
random_infill_matcher = re.compile(random_infill_pattern)

def generate_base64_random(length: int):
    if length < 6:
        raise ValueError(f'Refusing to acknowledge {length}-length random string')
    bytes_of_entropy = math.ceil(3/4 * length)
    tail_length = abs((bytes_of_entropy % 3) - 3) if (bytes_of_entropy % 3) else 0

    random_bytes = os.urandom(bytes_of_entropy)
    encoded = b''.join(
        base64.encodebytes(random_bytes).rstrip().split(b'\n')
    )

    if tail_length:
        encoded = encoded[:-tail_length]

    return encoded[:length].decode('ascii')


@dataclasses.dataclass
class Template:
    command_name: str
    path: pathlib.Path
    content: str
    infills: list[str]
    arguments_class: type
    fillers: dict[str, collections.abc.Callable]
    argument_values: object | None = None

    def __post_init__(self):
        for infill in set(self.infills):
            if infill not in self.fillers:
                self.fillers[infill] = self.argument_getter_getter(infill.strip('<>'))


    @classmethod
    def factory(cls, path: pathlib.Path):
        command_name = path.name.replace('.', '_')
        if path.parent != pathlib.Path(__file__).parent:
            command_name = '__'.join((path.parent.name, command_name))
        content = path.read_text()
        infills = infill_matcher.findall(content)
        unique_infills = set(infills)
        argument_keys = []
        fillers = {}
        for infill in set(infills):
            if random_match := random_infill_matcher.match(infill):
                random_length = int(random_match.group(1))
                fillers[infill] = functools.partial(generate_base64_random, random_length)
            else:
                argument_keys.append(infill.strip('<>'))
        arguments_class = cyclopts.Parameter(name="*")(
            dataclasses.make_dataclass(
                f'{command_name}_arguments',
                [(argument_key, str) for argument_key in argument_keys],
            ),
        )
        return cls(command_name, path, content, infills, arguments_class, fillers)


    def argument_getter_getter(self, argument):
        def getter():
            return getattr(self.argument_values, argument)
        return getter

    def populated(self):
        content = self.content
        for infill in self.infills:
            value = self.fillers[infill]()
            content = content.replace(infill, value, 1)
        return content

    def __repr__(self):
        return f'''
            {type(self).__name__}(
                command_name: {repr(self.command_name)},
                path: {repr(self.path)},
                content: "{self.content[-20:].replace('\n', '\\n')}...",
                infills: {repr(self.infills)},
                arguments_class: {repr(self.arguments_class)},
                fillers: {repr(self.fillers)},
                argument_values: {repr(self.argument_values)},
            )
        '''


def recursive_find_templates(path: pathlib.Path) -> list[pathlib.Path]:
    templates = []
    for entity in path.iterdir():
        if entity.is_dir():
            templates.extend(recursive_find_templates(entity))
        elif entity.is_file() and entity.suffix == '.TEMPLATE':
            templates.append(entity)
    return templates


def find_templates() -> list[Template]:
    root = pathlib.Path(__file__).parent
    template_paths = recursive_find_templates(root)
    return [Template.factory(template_path) for template_path in template_paths]


def attach_template_commands(app):
    templates = find_templates()
    for template in templates:
        def template_command(argument_values: template.arguments_class):
            template.argument_values = argument_values
            template.path.with_suffix('.POPULATED').write_text(
                template.populated(),
            )
        template_command.__name__ = template.command_name
        app.command(template_command)

if __name__ == '__main__':
    app = cyclopts.App()
    attach_template_commands(app)
    app()
