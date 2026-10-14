# Sean Collins Software License (SCSL v2.0)

**Copyright © 2025–2027 Sean Collins, 2 Paws Machine and Engineering. All rights reserved.**

---

### Preamble
This license governs the use, study, and compilation of the **AiLang** programming language, compiler, and associated core tools. It is engineered to allow open individual development, academic research, and unrestricted commercial deployment of compiled output, while legally protecting the integrity of the language specification, standard libraries, and official compiler distribution against unauthorized fragmentation, forks, and unlicensed commercial platform hosting.

---

### 1. Grant of Rights (Free Tiers)
Subject to the restrictions in Sections 3 and 4, the Copyright Holder grants you a perpetual, worldwide, non-exclusive, royalty-free license to download, use, and execute this software for:
- **Personal and Hobbyist Use:** Developing, testing, and running programs for individual projects.
- **Academic and Research Use:** Educational coursework, instructional demonstration, and academic experimentation.
- **Internal Non-Production Evaluation:** Testing, benchmarking, and internal prototyping within commercial or non-commercial organizations.

---

### 2. Runtime & Output Exception (Developer Ownership)
**Your compiled binaries belong solely to you.**
- **No Royalty on Output:** Programs compiled using this software—including output binaries containing embedded runtime routines, memory allocators (`Arena`), ELF headers, or standard library code (`Library.*`)—are entirely your property.
- **Commercial Distribution of Output:** You may license, distribute, sell, and execute programs compiled with AiLang under any license terms of your choosing (including closed-source and proprietary commercial licenses) without payment, attribution, or licensing fees owed to the Copyright Holder.

---

### 3. Language Specification & Forking Restrictions
To protect the uniformity of the language specification and prevent ecosystem fragmentation:
- **No Derivative Toolchains, Language Forks, or Tooling Mutation:** You may not publicly distribute modified versions of the compiler, compiler plugins, alternate dialects, derivative compilers, transpilers, or related tooling that alter or extend AiLang grammar tokens, syntax definitions, ABI calling conventions, or runtime semantics. AiLang, its grammar specification, and its core toolchain are closed to unauthorized modification and derivative distribution.
- **Permitted Forks for Upstream Contributions:** Public source-code forks (such as on GitHub or public git repositories) are permitted solely for private study, auditing, local patch generation, and submitting contributions directly upstream to the official AiLang repository.
- **Trademark & Brand Protection:** You may not use the names **AiLang**, **AIMacro**, or **2 Paws Machine and Engineering** in connection with any unauthorized or modified build of the compiler without express written permission from the Copyright Holder.
- **Specification Ownership:** The AiLang formal grammar, AST specification, and conformance test suites remain the exclusive intellectual property of Sean Collins and 2 Paws Machine and Engineering.

---

### 4. Commercial Triggers Requiring a Paid License
A separate commercial license from the Copyright Holder is required prior to engaging in any of the following activities:
- **Hosted Remote Compilation & Execution Services:** Running the compiler as part of a commercial cloud service, paid online playground, remote execution sandbox, automated API, or continuous integration platform charged to third parties.
- **AI Agent Sandboxes & Automated Platforms:** Integrating the compiler into commercial AI code-generation platforms, automated autonomous developer agent backends, or enterprise IDE integrations sold to customers.
- **Proprietary Toolchain Bundling:** Packaging the compiler executable or standard toolchain inside a proprietary commercial product, development environment, or hardware appliance.
- **Enterprise Production Deployments:** Deploying the compiler toolchain within a commercial enterprise for production compilation workflows across organizations exceeding ten (10) developers.

Inquiries, enterprise licensing, and custom terms are available by contacting:  
**smc.collins1977@gmail.com**

---

### 5. Disclaimer of Warranty and Limitation of Liability
THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDER AND CONTRIBUTORS “AS IS” AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.