target triple = "aarch64-pc-windows-msvc-elf"
define void @f() "frame-pointer"="all" {
  call void asm sideeffect "", "~{x19},~{x20},~{x21}"()
  ret void
}
