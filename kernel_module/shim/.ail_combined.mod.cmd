savedcmd_ail_combined.mod := printf '%s\n'   ail_shim.o ail_shim_pcie.o ail_payload.o | awk '!x[$$0]++ { print("./"$$0) }' > ail_combined.mod
