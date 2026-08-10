# Third-party notices

Ivaldi uses third-party software when building and running its launchers. This
file records the principal licensing considerations. It does not replace the
licence notices for dependencies contained in an application packaged by an
Ivaldi user.

## Nuitka

Ivaldi invokes Nuitka as a build tool to compile the Ivaldi launcher.

- Project: [Nuitka](https://github.com/Nuitka/Nuitka)
- Copyright: Copyright (c) 2008-2026 Kay Hayen and contributors
- Compiler licence: [GNU Affero General Public License, version 3](https://github.com/Nuitka/Nuitka/blob/4.1.3/LICENSE.txt)
- Runtime terms: [Nuitka Runtime Library Exception, version 1.0](https://github.com/Nuitka/Nuitka/blob/4.1.3/LICENSE-RUNTIME.txt)

The Runtime Library Exception permits executables and libraries produced by
Nuitka's compilation process to be conveyed under terms of the distributor's
choice when the exception's conditions are met. It does not change the AGPLv3
terms that apply to the Nuitka compiler itself.

Ivaldi does not incorporate or redistribute the Nuitka compiler as part of a
generated launcher. Anyone who separately redistributes or modifies Nuitka is
responsible for complying with the compiler's AGPLv3 terms.

## CPython

Nuitka-generated standalone and one-file launchers may include or link against
components of CPython.

- Project: [Python](https://www.python.org/)
- Licence: [Python Software Foundation License Version 2 and component notices](https://docs.python.org/3/license.html)

The applicable CPython licence and bundled component notices remain in effect
for those components.

## Packaged applications and dependencies

An Ivaldi launcher embeds the packaged application's wheel and may also embed
its dependency wheels. Those projects retain their own copyright and licence
terms. The person distributing a generated launcher is responsible for
including any notices, source offers, or other materials required by those
licences.
