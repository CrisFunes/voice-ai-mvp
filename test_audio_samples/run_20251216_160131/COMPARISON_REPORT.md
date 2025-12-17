# TTS ACCENT COMPARISON REPORT

**Generated:** 2025-12-16 16:02:06

**Total Samples:** 6
**Total Cost:** $0.03 USD

---

## 📊 RESULTS BY TEXT TYPE

### 1. Saludo profesional

**Text:** _Buongiorno, sono il suo commercialista di fiducia. Come posso aiutarla oggi?_

| Model | Voice | Method | Cost | File |
|-------|-------|--------|------|------|
| tts-1-hd | alloy | standard | $0.0023 | `greeting_tts1hd_alloy.mp3` |
| gpt-4o-audio-preview | alloy | accent_steered_strong | $0.0046 | `greeting_gpt4o_audio_alloy_strong.mp3` |
| gpt-4o-audio-preview | nova | accent_steered_strong | $0.0046 | `greeting_gpt4o_audio_nova.mp3` |

### 2. Términos técnicos fiscales

**Text:** _La dichiarazione IVA trimestrale deve essere presentata entro il giorno quindici del mese successivo al trimestre di riferimento._

| Model | Voice | Method | Cost | File |
|-------|-------|--------|------|------|
| tts-1-hd | alloy | standard | $0.0039 | `technical_tts1hd_alloy.mp3` |
| gpt-4o-audio-preview | alloy | accent_steered_strong | $0.0077 | `technical_gpt4o_audio_alloy_strong.mp3` |
| gpt-4o-audio-preview | nova | accent_steered_strong | $0.0077 | `technical_gpt4o_audio_nova.mp3` |

### 3. Números y porcentajes

**Text:** _L'aliquota IRES ordinaria è del ventiquattro per cento, mentre per le società di capitali l'IVA può variare dal quattro al ventidue per cento._


### 4. Respuesta compleja (real)

**Text:** _Dunque, per quanto riguarda la sua domanda sulle deduzioni fiscali, le spiego meglio. Secondo la normativa vigente, le spese di carburante sono deducibili al venti per cento per i veicoli aziendali. Tuttavia, se il veicolo è utilizzato esclusivamente per l'attività professionale, la percentuale di deduzione può aumentare fino all'ottanta per cento. Le consiglio di conservare tutti i documenti giustificativi._


### 5. Palabras difíciles de pronunciar

**Text:** _Gli adempimenti fiscali richiedono particolare attenzione: dichiarazione, registrazione, liquidazione, ritenuta d'acconto, contribuzione previdenziale._


---

## 🎯 CONFIGURATIONS TESTED

### OpenAI tts-1 (standard) - Voice: alloy

- **Model:** tts-1
- **Voice:** alloy
- **Method:** standard
- **Cost:** $0.015 per 1K chars
- **Description:** Modelo estándar, calidad básica, acento neutral/anglófono

### OpenAI tts-1 (standard) - Voice: nova

- **Model:** tts-1
- **Voice:** nova
- **Method:** standard
- **Cost:** $0.015 per 1K chars
- **Description:** Modelo estándar, voz femenina, acento neutral

### OpenAI tts-1 (standard) - Voice: echo

- **Model:** tts-1
- **Voice:** echo
- **Method:** standard
- **Cost:** $0.015 per 1K chars
- **Description:** Modelo estándar, voz masculina, acento neutral

### OpenAI tts-1-hd (high def) - Voice: alloy

- **Model:** tts-1-hd
- **Voice:** alloy
- **Method:** standard
- **Cost:** $0.030 per 1K chars
- **Description:** Modelo HD, mejor calidad audio, PERO sigue con acento anglófono

### OpenAI tts-1-hd (high def) - Voice: nova

- **Model:** tts-1-hd
- **Voice:** nova
- **Method:** standard
- **Cost:** $0.030 per 1K chars
- **Description:** Modelo HD, voz femenina, acento neutral

### GPT-4o Audio Preview - Accent: Italian (light instructions)

- **Model:** gpt-4o-audio-preview
- **Voice:** alloy
- **Method:** accent_steered_light
- **Cost:** $0.060 per 1K chars
- **Description:** Modelo avanzado con instrucciones LIGERAS de acento italiano

### GPT-4o Audio Preview - Accent: Italian (strong instructions)

- **Model:** gpt-4o-audio-preview
- **Voice:** alloy
- **Method:** accent_steered_strong
- **Cost:** $0.060 per 1K chars
- **Description:** Modelo avanzado con instrucciones FUERTES de acento milanés

### GPT-4o Audio Preview - Voice: nova + Italian accent

- **Model:** gpt-4o-audio-preview
- **Voice:** nova
- **Method:** accent_steered_strong
- **Cost:** $0.060 per 1K chars
- **Description:** Modelo avanzado, voz femenina, acento italiano fuerte

---

## 🎧 HOW TO COMPARE

1. **Busca el mismo texto** en diferentes archivos (ej: `greeting_*.mp3`)
2. **Escucha las versiones** una tras otra
3. **Evalúa:**
   - ¿Suena italiano nativo o extranjero?
   - ¿Las vocales son italianas o anglófonas?
   - ¿La entonación es natural?
   - ¿La pronunciación de términos técnicos es correcta?

## 💡 RECOMMENDATIONS

**Para DEMO rápido (precio bajo):**
- `tts1hd_alloy` o `tts1hd_nova` (mejor calidad que tts-1)
- Costo: ~$0.03/1K chars
- Limitación: Acento anglófono persiste

**Para PRODUCCIÓN (calidad profesional):**
- `gpt4o_audio_alloy_strong` (acento italiano fuerte)
- Costo: ~$0.06/1K chars (2x más caro que HD)
- Ventaja: Acento italiano nativo

**Si NINGUNO convence:**
- Migrar a ElevenLabs (voces nativas italianas reales)
- Costo: ~$0.30/1K chars (5x más caro)
- Garantía: Calidad profesional broadcasting

