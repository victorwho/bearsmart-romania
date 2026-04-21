# GPT Store public launch checklist

## Cloud Run
- [ ] serviciul răspunde public la `/health`
- [ ] `/privacy-policy` este public și conține textul final
- [ ] `/openapi-gpt.json` este accesibil
- [ ] `ENABLE_DOCS=false` în producție

## GPT Builder
- [ ] Action importat din `/openapi-gpt.json` sau `openapi_for_gpt_public.yaml`
- [ ] Instructions actualizate cu `gpt_action_instruction_patch_public.txt`
- [ ] Privacy Policy URL setat către `/privacy-policy`
- [ ] GPT testat în Preview pe minim 5 cazuri

## Produs și siguranță
- [ ] nu sunt trimise imagini brute către API
- [ ] payloadurile sunt validate strict
- [ ] logurile nu conțin date sensibile inutile
- [ ] schema Action nu expune endpointuri inutile
