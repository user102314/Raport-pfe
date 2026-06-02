# Cycle 4 — Diagrammes Mermaid

Sources Mermaid des diagrammes du chapitre **Cycle 4 — Logiciel
Raspberry Pi** du rapport PFE.

Tous les fichiers `.mmd` de ce dossier sont rendus en PNG dans
`Raport-pfe/public/` avec le préfixe `koda-cycle4-*` puis insérés via
`\IfFileExists` dans `finalyearrapport.tex`.

## Rendu manuel (un seul fichier)

```bash
npx -p @mermaid-js/mermaid-cli mmdc \
  -i mermaid/ch4-cycle4/<source>.mmd \
  -o public/<output>.png \
  -t default -b transparent -w 3508 -H 2480
```

(`3508 × 2480 px` = A3 paysage 300 dpi — lisible imprimé.)

## Rendu en lot (PowerShell)

```powershell
Get-ChildItem mermaid/ch4-cycle4/*.mmd | ForEach-Object {
    $out = "public/$($_.BaseName -replace '^koda-ch4-','koda-cycle4-').png"
    npx -p @mermaid-js/mermaid-cli mmdc -i $_.FullName -o $out `
        -t default -b transparent -w 3508 -H 2480
}
```

## Fichiers présents

| Source Mermaid | Cible PNG | Usage dans la chapitre |
|---|---|---|
| `koda-ch4-architecture-globale.mmd`        | `koda-cycle4-architecture-globale.png`        | Architecture logicielle globale |
| `koda-ch4-arborescence-code.mmd`           | `koda-cycle4-arborescence-code.png`           | Architecture du code (packages) |
| `koda-ch4-classes-services.mmd`            | `koda-cycle4-classes-services.png`            | Diagramme de classes UML |
| `koda-ch4-sequence-boot.mmd`               | `koda-cycle4-sequence-boot.png`               | Séquence de boot parallèle |
| `koda-ch4-machine-etats.mmd`               | `koda-cycle4-machine-etats.png`               | Machine d'états du robot |
| `koda-ch4-wake-word-hybride.mmd`           | `koda-cycle4-wake-word-hybride.png`           | État interne Hybrid Vosk + Azure |
| `koda-ch4-sequence-tour-de-parole.mmd`     | `koda-cycle4-sequence-tour-de-parole.png`     | Séquence d'un tour de parole |
| `koda-ch4-rotation-mpu6050.mmd`            | `koda-cycle4-rotation-mpu6050.png`            | Rotation closed-loop MPU6050 |
| `koda-ch4-dispatch-actions.mmd`            | `koda-cycle4-dispatch-actions.png`            | Dispatch des 5 types d'actions |
| `koda-ch4-touch-interruption.mmd`          | `koda-cycle4-touch-interruption.png`          | Interruption capteur tactile |
| `koda-ch4-pcm-broadcaster.mmd`             | `koda-cycle4-pcm-broadcaster.png`             | Fan-out PCM 1→N |

> **Note** : le chapitre LaTeX utilise `\IfFileExists{public/<png>}` ;
> si une image manque, le bloc figure est silencieusement omis et la
> compilation continue. Cela permet d'éditer le chapitre avant que les
> PNG soient générés.
