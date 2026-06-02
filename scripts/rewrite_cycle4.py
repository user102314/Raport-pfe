"""Surgical replacement of the Cycle 4 chapter in finalyearrapport.tex.

Reads the file as bytes, finds the chapter window between the markers we
control (\\chapter{Cycle 4 ...} and the next \\chapter{...}), replaces it with
the freshly drafted block, preserves the original CRLF + tab indentation
style, and writes the file back.

Idempotent: running it twice is fine — it always replaces the *current*
content of the window.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEX = ROOT / "finalyearrapport.tex"

START_MARK = b"\t\\chapter{Cycle 4 : Syst\xc3\xa8me Embarqu\xc3\xa9 --- Partie Logicielle Raspberry Pi}"
# We stop just before the Cycle 5 chapter (the next \chapter).
END_MARK = b"\\chapter{Cycle 5"


def _indent_with_tabs(body: str) -> str:
    """Every non-empty content line in this report block starts with a tab.

    We accept the new chapter as plain text (LF, no indent) and translate it
    to the original style: every line gets one leading tab, line endings are
    converted to CRLF. Blank lines also keep a tab so the visual gutter is
    preserved — matches the rest of the file.
    """
    out_lines: list[str] = []
    for line in body.splitlines():
        if line == "":
            out_lines.append("\t")
        else:
            out_lines.append("\t" + line)
    # Ensure trailing CRLF before next chapter.
    return "\r\n".join(out_lines) + "\r\n"


NEW_CHAPTER = r"""\chapter{Cycle 4 : Système Embarqué --- Partie Logicielle Raspberry Pi}
\chaptermark{Cycle 4 --- Logiciel Raspberry Pi}

%------------------------------------------------------------------
\section{Introduction}
%------------------------------------------------------------------

Le \textbf{Cycle~3} a validé la plateforme matérielle de KODA : Raspberry Pi,
Arduino, ReSpeaker, écran Nextion, caméra, sortie audio et alimentation. Le
\textbf{Cycle~4} transforme cette plateforme physique en un \textbf{robot
compagnon autonome} capable de réagir en continu à la voix et au toucher, de
dialoguer avec l'utilisateur et d'exécuter les décisions produites par le
Distributeur de Services et le moteur n8n.

Ce chapitre présente la \textbf{partie logicielle embarquée Raspberry Pi}
telle qu'elle est implémentée dans le dossier \texttt{codeRaspberry/}. Le
programme principal est lancé par la commande \texttt{python -m app.main} et
repose sur une architecture Python \textbf{asynchrone} en couches, organisée
autour de \textbf{services métier} de haut niveau et d'\textbf{adaptateurs
matériels} interchangeables. Le Raspberry Pi n'est pas le cerveau
conversationnel complet de KODA ; il joue plutôt le rôle de \textbf{corps
opérationnel} : il écoute en permanence un mot de réveil, s'oriente vers le
locuteur grâce à la DOA du ReSpeaker, capture la question jusqu'au silence,
interroge le backend FastAPI, affiche une expression sur l'écran Nextion,
prononce la réponse synthétisée, joue la musique téléchargée et transmet les
mouvements à l'Arduino qui ferme la boucle de rotation avec un gyroscope
MPU6050.

Par rapport au prototype initial, la version actuelle du logiciel ajoute :
\begin{itemize}[noitemsep]
	\item un moteur de mot de réveil \textbf{hybride} (Vosk local + Azure
	WebSocket) pour combiner faible latence et robustesse multilingue ;
	\item une \textbf{rotation en boucle fermée MPU6050} qui remplace la
	temporisation open-loop par une intégration gyroscopique côté Arduino ;
	\item un \textbf{capteur tactile} avec interruption GPIO qui suspend toute
	action en cours pour jouer une réaction « chatouilles » ;
	\item une \textbf{reconnaissance faciale} déléguée au backend, mise en
	cache et rafraîchie en arrière-plan, qui personnalise les réponses ;
	\item un \textbf{lecteur de musique} qui télécharge le morceau depuis le
	backend (la Raspberry n'ayant pas accès Internet sur le réseau ISET) ;
	\item un \textbf{registre de sous-processus} qui garantit que \texttt{sox},
	\texttt{paplay} ou \texttt{rpicam} ne laissent pas de zombies après un
	arrêt brutal.
\end{itemize}

\begin{tcolorbox}[colback=blue!5!white, colframe=blue!60!black,
	title=\textbf{Objectif du Cycle 4}]
	Implémenter et valider le logiciel embarqué Raspberry Pi qui relie les
	composants matériels du robot au backend FastAPI : mot de réveil hybride,
	orientation closed-loop, capture vocale VAD, dispatch des cinq types
	d'actions n8n (texte, musique, mouvement, sommeil, erreur), affichage
	Nextion, reconnaissance faciale, capteur tactile et arrêt propre. Les
	cibles de latence sont \textbf{< 300\,ms} pour le mot de réveil et
	\textbf{< 3\,s} pour le premier token vocal de la réponse.
\end{tcolorbox}

%------------------------------------------------------------------
\section{Architecture logicielle globale}
%------------------------------------------------------------------

Le logiciel Raspberry Pi est conçu comme une \textbf{couche d'orchestration
locale}. Il démarre tous les adaptateurs en parallèle, vérifie les
dépendances matérielles au boot, puis exécute une boucle asynchrone unique
qui alterne entre un mode \textbf{passif} (attente du mot de réveil) et un
mode \textbf{actif} (dialogue avec l'utilisateur). Les traitements lourds de
compréhension, de décision et de synthèse vocale restent délégués au
\textbf{Distributeur FastAPI}, qui relaie l'information vers n8n, Supabase et
les services cloud (Azure Speech).

L'architecture suit quatre niveaux complémentaires :
\begin{itemize}
	\item \textbf{Point d'entrée} (\texttt{app/}) : \texttt{main.py}, qui
	exécute la séquence de démarrage parallèle, installe les handlers
	\texttt{SIGINT}/\texttt{SIGTERM}, lance la boucle \emph{wake-word + touch}
	puis effectue l'arrêt propre.
	\item \textbf{Configuration} (\texttt{app/config.py}) : centralise les
	dataclasses chargées depuis \texttt{.env} (réseau backend, ReSpeaker,
	Vosk, hybride wake-word, rotation, touch, face recognition, caméra,
	Bluetooth).
	\item \textbf{Services métier} (\texttt{services/}) : modules
	indépendants du matériel — conversation, wake word, écoute VAD,
	affichage, mouvement, musique, voix, vision, capteur tactile.
	\item \textbf{Adaptateurs} (\texttt{adapters/}) : interfaces concrètes
	vers le monde externe — HTTP/WebSocket vers le backend, ReSpeaker (sox),
	Nextion (UART), Arduino (USB série), audio (Bluetooth/PulseAudio),
	caméra (MJPEG ou \texttt{rpicam}).
\end{itemize}

\IfFileExists{public/koda-cycle4-architecture-globale.png}{%
	\begin{figure}[htbp]
		\centering
		\includegraphics[width=0.98\textwidth]{public/koda-cycle4-architecture-globale.png}
		\caption{Cycle~4 --- architecture logicielle globale du logiciel Raspberry Pi (services, adaptateurs et environnement externe)}
		\label{fig:ch4-architecture-globale}
	\end{figure}
}{}

%------------------------------------------------------------------
\section{Architecture du code et diagramme de classes}
%------------------------------------------------------------------

Le projet \texttt{codeRaspberry} est volontairement séparé en dossiers
courts et lisibles. Chaque adaptateur peut être testé indépendamment du
robot complet, et le programme principal ne manipule jamais directement les
détails série, sox ou HTTP : il passe par les services, qui passent par les
adaptateurs.

\IfFileExists{public/koda-cycle4-arborescence-code.png}{%
	\begin{figure}[htbp]
		\centering
		\includegraphics[width=0.98\textwidth]{public/koda-cycle4-arborescence-code.png}
		\caption{Cycle~4 --- arborescence du dossier \texttt{codeRaspberry/} (packages, modules clés et firmware Arduino)}
		\label{fig:ch4-arborescence-code}
	\end{figure}
}{}

Le diagramme de classes UML ci-dessous présente les objets logiciels qui
coopèrent pendant une interaction. \texttt{ConversationService} est
l'orchestrateur fonctionnel d'un tour de parole : il récupère l'audio via
\texttt{ContinuousListenerService}, appelle \texttt{BackendClient}, puis
déclenche l'action retournée via \texttt{SpeechService},
\texttt{MotionDispatcher}, \texttt{MusicPlayer} ou \texttt{DisplayService}.
La détection du mot de réveil est portée par \texttt{WakeWordService} et son
moteur \texttt{HybridWakeWordEngine}, qui multiplexe Vosk et un WebSocket
Azure.

\IfFileExists{public/koda-cycle4-classes-services.png}{%
	\begin{figure}[htbp]
		\centering
		\includegraphics[width=0.98\textwidth]{public/koda-cycle4-classes-services.png}
		\caption{Cycle~4 --- diagramme de classes UML : services métier et adaptateurs matériels}
		\label{fig:ch4-classes-services}
	\end{figure}
}{}

%------------------------------------------------------------------
\section{Configuration et lancement}
%------------------------------------------------------------------

L'exécution se fait depuis le dossier \texttt{codeRaspberry/}. Les variables
d'environnement permettent d'adapter le même code à un robot donné sans
modifier les sources Python. Toutes les valeurs ont un défaut raisonnable
dans \texttt{app/config.py} ; le fichier \texttt{.env} ne contient que les
\emph{overrides} propres au robot (adresse backend, identifiant, MAC du
hauteparleur Bluetooth, etc.).

\begin{lstlisting}[style=kodatest, language=shellkoda, caption={Lancement du logiciel embarqué Raspberry Pi}]
source .venv/bin/activate
export BACKEND_URL=http://192.168.69.185:8000
export ROBOT_ID=koda-01
export RESPEAKER_DEVICE=pipewire           # ALSA->PipeWire, pas plughw:3,0
export VOSK_LANGUAGE=ar                    # mgb2 arabe
export HYBRID_WAKE_WORD_ENABLED=1
export HYBRID_WAKE_WORD_AWAITING_TIMEOUT=4.0
export ROTATION_ENABLED=1
export TOUCH_ENABLED=1                     # GPIO BCM 17 par defaut
export FACE_RECOGNITION_ENABLED=1
python -m app.main
\end{lstlisting}

Les paramètres essentiels sont :
\begin{itemize}
	\item \textbf{\texttt{BACKEND\_URL}} : adresse HTTP du Distributeur
	FastAPI sur le même réseau que la Raspberry (utilisée aussi pour la
	WebSocket \texttt{/api/ws/wake-word/\{robot\_id\}}).
	\item \textbf{\texttt{RESPEAKER\_DEVICE}} : périphérique de capture sox.
	\texttt{pipewire} est préféré car la firmware XMOS refuse parfois le
	\texttt{set\_freq} 16~kHz issu de \texttt{plughw:3,0}.
	\item \textbf{\texttt{VOSK\_LANGUAGE}} : code de langue du modèle Vosk
	(\texttt{ar} = arabe \texttt{mgb2}, \texttt{fr}, \texttt{en}, etc.).
	\item \textbf{\texttt{HYBRID\_WAKE\_WORD\_*}} : active la double détection
	Vosk + Azure WS et le délai d'attente Azure après un déclenchement Vosk.
	\item \textbf{\texttt{ROTATION\_ENABLED}}, \texttt{TOUCH\_ENABLED},
	\texttt{FACE\_RECOGNITION\_ENABLED} : commutateurs principaux qui
	permettent de démarrer en mode dégradé contrôlé si un composant manque.
	\item \textbf{Audio sortie} : MAC Bluetooth ou \texttt{pulse\_sink} dans
	\texttt{AUDIO\_OUTPUT\_*}. Bascule automatique vers le sink par défaut
	si le speaker BT n'est pas joignable.
\end{itemize}

%------------------------------------------------------------------
\section{Démarrage parallèle et diagnostic matériel}
%------------------------------------------------------------------

Au démarrage, \texttt{app.main} installe un \texttt{ThreadPoolExecutor}
dédié aux appels bloquants (\texttt{KODA\_THREAD\_WORKERS}), exécute la
fonction \texttt{run\_full\_check()} qui dresse un rapport composant par
composant, puis ouvre les adaptateurs série Nextion et Arduino en
\textbf{parallèle}. Tous les services qui n'ont aucune dépendance les uns
sur les autres sont ensuite lancés dans un unique \texttt{asyncio.gather} :
\texttt{backend.start()}, sonde \texttt{/health}, connexion Bluetooth,
chargement du modèle Vosk (~\!8\,s sur Pi~4), initialisation USB de la
\texttt{DOAReader}, retour de l'écran à son frame idle et geste de
salutation. Le \emph{coût total} du boot est ramené à celui de la tâche la
plus lente (généralement Bluetooth ou Vosk) au lieu de la somme des
temps unitaires.

L'option \texttt{return\_exceptions=True} du \texttt{gather} garantit
qu'\textbf{un échec de bootstrap (Bluetooth absent, backend indisponible,
hauteparleur déconnecté) ne tue pas les autres} : chaque tâche est isolée,
loguée et marquée comme dégradée. Le robot peut ainsi démarrer même si la
caméra ou le speaker manquent.

\IfFileExists{public/koda-cycle4-sequence-boot.png}{%
	\begin{figure}[htbp]
		\centering
		\includegraphics[width=0.98\textwidth]{public/koda-cycle4-sequence-boot.png}
		\caption{Cycle~4 --- séquence de démarrage parallèle (\texttt{app.main.run})}
		\label{fig:ch4-sequence-boot}
	\end{figure}
}{}

%------------------------------------------------------------------
\section{Boucle principale et machine d'états}
%------------------------------------------------------------------

Après l'initialisation, le robot entre dans la fonction
\texttt{\_run\_robot\_loop\_with\_touch}, qui combine la boucle
comportementale principale et la surveillance du capteur tactile via un
\texttt{asyncio.wait(\dots, return\_when=FIRST\_COMPLETED)}. En mode passif,
il écoute le mot de réveil ; détecté, il affiche \texttt{SURPRISED},
s'oriente vers l'utilisateur par DOA puis MPU6050, prononce une salutation
en parallèle, et lance la capture VAD de la question. Le retour du backend
décide ensuite du comportement : réponse vocale, musique, mouvement,
sommeil ou erreur. Une interruption tactile peut, à tout moment, annuler la
tâche en cours et déclencher une réaction « chatouilles » avant le retour à
l'état passif.

\IfFileExists{public/koda-cycle4-machine-etats.png}{%
	\begin{figure}[htbp]
		\centering
		\includegraphics[width=0.92\textwidth]{public/koda-cycle4-machine-etats.png}
		\caption{Cycle~4 --- machine d'états logicielle du robot (passif, actif, touch, sommeil)}
		\label{fig:ch4-machine-etats}
	\end{figure}
}{}

%------------------------------------------------------------------
\section{Pipeline vocal : mot de réveil hybride Vosk + Azure}
%------------------------------------------------------------------

Le pipeline vocal est le cœur de l'expérience utilisateur. Il combine trois
traitements complémentaires :
\begin{itemize}
	\item \textbf{Détection locale du mot de réveil par Vosk} : le moteur
	\texttt{VoskWakeWordEngine} consomme un flux PCM 16~kHz mono issu du
	ReSpeaker via sox (\texttt{remix~1} sur le canal XMOS traité ch0, suivi
	d'un \texttt{-c~1} obligatoire en sortie raw). Aucun appel cloud n'est
	fait tant qu'un candidat n'est pas détecté.
	\item \textbf{Confirmation par Azure WebSocket} : lorsque
	\texttt{HYBRID\_WAKE\_WORD\_ENABLED=1}, le moteur
	\texttt{HybridWakeWordEngine} bascule de l'état \textsc{SLEEP} à
	\textsc{AWAITING} dès le premier déclenchement Vosk. Il ouvre alors un
	WebSocket vers \texttt{/api/ws/wake-word/\{robot\_id\}} sur le backend
	(qui relaie le PCM à Azure Speech) et fait une \emph{course} : le premier
	moteur qui confirme le mot-clé l'emporte ; sinon, le moteur revient en
	\textsc{SLEEP} après \texttt{awaiting\_timeout\_s}.
	\item \textbf{Écoute active VAD} : après le réveil,
	\texttt{ContinuousListenerService} capture la question complète jusqu'à
	une période de silence configurable, au lieu d'imposer une durée fixe ;
	un \emph{seuil minimum} (\texttt{min\_speech\_seconds}) évite d'envoyer
	un WAV de 44 octets quand sox est encore en train de démarrer.
	\item \textbf{Traitement distant} : le WAV est envoyé en HTTP au backend
	sur \texttt{POST /api/audio/speech-to-action}. La réponse est un objet
	\texttt{ActionResult} contenant le type d'action, le texte reconnu, le
	texte à prononcer, l'audio TTS encodé en base64 et éventuellement une
	URL de musique ou une commande de mouvement.
\end{itemize}

\IfFileExists{public/koda-cycle4-wake-word-hybride.png}{%
	\begin{figure}[htbp]
		\centering
		\includegraphics[width=0.92\textwidth]{public/koda-cycle4-wake-word-hybride.png}
		\caption{Cycle~4 --- machine d'états interne du moteur \texttt{HybridWakeWordEngine} (Vosk gate, Azure race, timeout)}
		\label{fig:ch4-wake-word-hybride}
	\end{figure}
}{}

\IfFileExists{public/koda-cycle4-sequence-tour-de-parole.png}{%
	\begin{figure}[htbp]
		\centering
		\includegraphics[width=0.98\textwidth]{public/koda-cycle4-sequence-tour-de-parole.png}
		\caption{Cycle~4 --- séquence complète d'un tour de parole : wake → rotation → greeting → écoute → backend → dispatch}
		\label{fig:ch4-sequence-tour-de-parole}
	\end{figure}
}{}

%------------------------------------------------------------------
\section{Capture audio multi-consommateurs}
%------------------------------------------------------------------

Plusieurs services veulent lire le même flux microphone en même temps :
Vosk pour le mot de réveil, le client WebSocket Azure pendant
\textsc{AWAITING}, et la VAD lors de la capture de la question. Plutôt que
de relancer sox à chaque besoin (ce qui provoquait des conflits de
périphérique USB), le service \texttt{PCMBroadcaster} adopte un schéma
\textbf{un producteur, N consommateurs} : un unique processus sox écrit
dans une file de trames, chaque consommateur dispose d'une queue
\texttt{asyncio} \textbf{bornée}. Un consommateur lent voit ses anciennes
trames droppées sans pénaliser les autres.

\IfFileExists{public/koda-cycle4-pcm-broadcaster.png}{%
	\begin{figure}[htbp]
		\centering
		\includegraphics[width=0.86\textwidth]{public/koda-cycle4-pcm-broadcaster.png}
		\caption{Cycle~4 --- broadcaster PCM : un producteur sox, plusieurs consommateurs (Vosk, Azure WS, VAD)}
		\label{fig:ch4-pcm-broadcaster}
	\end{figure}
}{}

%------------------------------------------------------------------
\section{Rotation closed-loop avec MPU6050}
%------------------------------------------------------------------

Pour orienter le robot vers le locuteur, le Raspberry Pi lit la direction
d'arrivée du son (DOA) fournie par le ReSpeaker via le registre USB HID du
XMOS, puis convertit cet angle brut en rotation signée
$[-180^\circ, +180^\circ]$ selon la convention \emph{positif = horaire,
négatif = anti-horaire}, en tenant compte du \texttt{front\_offset\_deg} et
du flag \texttt{invert\_direction} pour absorber l'orientation mécanique du
micro.

L'innovation majeure du Cycle~4 est de remplacer la temporisation
\textbf{open-loop} (\texttt{durée = angle / vitesse}) par une rotation
\textbf{en boucle fermée} basée sur le gyroscope MPU6050 câblé sur les
broches \texttt{A4} (SDA) et \texttt{A5} (SCL) de l'Arduino. Le firmware
\texttt{koda\_arduino.ino} expose un protocole étendu en plus du jeu
historique de commandes mono-caractère :

\begin{lstlisting}[style=kodatest, language=shellkoda, caption={Protocole de rotation MPU6050 (firmware Arduino \texttt{koda\_arduino.ino})}]
# Commandes legacy (immediates, sans reponse)
F  B  S  L  R          # forward/backward/stop/left/right (continu)
H  T  G  D  A          # hello, head, left arm, right arm, all servos
+  -                   # speed up / down
?                      # status -> STATUS:speed=N,gyro=ok|nok\n

# Protocole etendu rotation (bloquant, avec reponse)
R045\n                 # tourner a droite de 45 degres
L180\n                 # tourner a gauche de 180 degres
DONE:46\n              # succes (degres reellement parcourus)
ERR:timeout\n          # echec (safety 6 s firmware)
ERR:nogyro\n           # MPU6050 absent / I2C muet au boot
\end{lstlisting}

Côté Pi, \texttt{MotionService.rotate\_by\_angle} envoie
\texttt{send\_line("R045", read\_timeout\_s=\dots)} et attend la ligne
\texttt{DONE:<actual>}. Le firmware, lui, intègre la vitesse angulaire
$\omega_z$ du gyroscope à 200~Hz, freine sur les 6 derniers degrés en
abaissant le PWM à 110 (constante \texttt{ROTATION\_BRAKE\_SPEED}), stoppe
les moteurs et attend 150~ms supplémentaires que le châssis se stabilise.
La précision typique passe de \textbf{$\pm$5--10$^\circ$} (open-loop,
sensible à la tension batterie et au frottement) à \textbf{$\pm$2$^\circ$}
quelle que soit la charge.

\IfFileExists{public/koda-cycle4-rotation-mpu6050.png}{%
	\begin{figure}[htbp]
		\centering
		\includegraphics[width=0.92\textwidth]{public/koda-cycle4-rotation-mpu6050.png}
		\caption{Cycle~4 --- rotation en boucle fermée : Pi $\rightarrow$ Arduino $\rightarrow$ MPU6050 $\rightarrow$ DONE/ERR}
		\label{fig:ch4-rotation-mpu6050}
	\end{figure}
}{}

\textbf{Sécurités} : un timeout firmware de 6~s coupe la rotation si le
gyroscope renvoie des valeurs aberrantes ou si le châssis est bloqué ; le
Pi reçoit alors \texttt{ERR:timeout} et envoie un \texttt{STOP} défensif.
Si la MPU6050 n'a pas répondu à l'I2C au boot, toute commande
\texttt{Rxxx}/\texttt{Lxxx} retourne immédiatement \texttt{ERR:nogyro}
sans alimenter les moteurs. Une consigne \texttt{|angle|} inférieure à
\texttt{deadband\_deg} (par défaut 5$^\circ$) est ignorée pour préserver la
batterie. Côté Pi, le \texttt{asyncio.Lock} du \texttt{MotionService}
sérialise les commandes Arduino ; les appels concurrents (par exemple
\texttt{hello()} pendant une rotation) sont mis en file sans blocage du
reste de la boucle.

%------------------------------------------------------------------
\section{Dispatch des actions retournées par le backend}
%------------------------------------------------------------------

Le backend interprète la réponse de n8n (qui peut prendre six formes
différentes : JSON texte, JSON musique, texte direction brut, « I am
Closed », « Yo Yo », message de sommeil) et la normalise en un
\texttt{ActionResult} structuré. Côté Raspberry,
\texttt{ConversationService} applique alors cinq branches métier :

\begin{table}[H]
	\centering
	\caption{Cycle~4 --- les cinq types d'actions dispatchés côté Pi}
	\label{tab:ch4-actions}
	\renewcommand{\arraystretch}{1.25}
	\begin{tabularx}{\textwidth}{|>{\raggedright\arraybackslash}p{2.2cm}|>{\raggedright\arraybackslash}X|>{\raggedright\arraybackslash}p{3.4cm}|}
		\hline
		\textbf{\texttt{type}} & \textbf{Comportement} & \textbf{Services impliqués} \\
		\hline
		\texttt{text}   & Expression \texttt{SINGING}, lecture de l'audio TTS reçu en base64, retour idle & \texttt{Display}, \texttt{Speech}, \texttt{AudioOutput} \\
		\hline
		\texttt{music}  & Annonce vocale, téléchargement depuis le backend (cache local \texttt{cache/music/}), lecture avec \texttt{paplay} & \texttt{Speech}, \texttt{MusicPlayer}, \texttt{BackendClient} \\
		\hline
		\texttt{motion} & Commande \texttt{forward}, \texttt{backward}, \texttt{left}, \texttt{right} ou \texttt{stop} via \texttt{MotionDispatcher} & \texttt{Motion}, \texttt{Arduino} \\
		\hline
		\texttt{sleep}  & Message d'au revoir, expression \texttt{SLEEPING}, retour en mode passif & \texttt{Speech}, \texttt{Display} \\
		\hline
		\texttt{error}  & Expression \texttt{SAD} brève, log structuré, reprise de la boucle & \texttt{Display} \\
		\hline
	\end{tabularx}
\end{table}

\IfFileExists{public/koda-cycle4-dispatch-actions.png}{%
	\begin{figure}[htbp]
		\centering
		\includegraphics[width=0.96\textwidth]{public/koda-cycle4-dispatch-actions.png}
		\caption{Cycle~4 --- flowchart de dispatch des actions retournées par le backend}
		\label{fig:ch4-dispatch-actions}
	\end{figure}
}{}

%------------------------------------------------------------------
\section{Affichage Nextion et expressions}
%------------------------------------------------------------------

L'écran Nextion n'est pas piloté pixel par pixel : les images et
animations sont préparées dans l'éditeur Nextion, et le Pi se contente
d'envoyer des commandes série courtes (\texttt{tm0.en=0},
\texttt{page facegif}, \texttt{ref}). \texttt{DisplayService} sérialise ces
commandes avec un verrou \texttt{asyncio} afin d'éviter qu'une expression
en cours de transition soit écrasée par une autre. Pendant une réponse
vocale, le service peut désactiver temporairement le timer de clignement,
afficher une expression fixe, puis restaurer l'état idle.

\begin{table}[H]
	\centering
	\caption{Expressions logicielles envoyées à l'écran Nextion}
	\label{tab:ch4-expressions-nextion}
	\renewcommand{\arraystretch}{1.2}
	\begin{tabular}{|l|l|}
		\hline
		\textbf{Expression} & \textbf{Usage principal} \\
		\hline
		\texttt{NEUTRAL}    & Attente et retour idle \\
		\hline
		\texttt{SURPRISED}  & Mot de réveil détecté \\
		\hline
		\texttt{THINKING}   & Capture ou traitement de la question \\
		\hline
		\texttt{SINGING}    & Réponse vocale ou musique \\
		\hline
		\texttt{HAPPY}      & Interruption tactile (chatouilles) \\
		\hline
		\texttt{SAD}        & Erreur ou échec de traitement \\
		\hline
		\texttt{SLEEPING}   & Passage en sommeil ou arrêt \\
		\hline
	\end{tabular}
\end{table}

%------------------------------------------------------------------
\section{Reconnaissance faciale}
%------------------------------------------------------------------

Lorsque \texttt{FACE\_RECOGNITION\_ENABLED=1},
\texttt{FaceRecognitionService} déclenche en arrière-plan une capture
\texttt{CameraAdapter} (MJPEG en priorité, fallback \texttt{rpicam-still})
dès la détection du mot de réveil. La photo est envoyée à
\texttt{/api/identify-face} sur le backend ; le nom retourné est mis en
cache (TTL configurable, par défaut 60~s) puis injecté comme
\texttt{extra\_text} dans la requête \texttt{speech-to-action}. Le prompt
côté n8n peut ainsi personnaliser la réponse (« Bonjour Salah ») sans
appel additionnel.

Le rafraîchissement est \emph{fire-and-forget} : la tâche
\texttt{asyncio} est tracée par \texttt{self.\_refresh\_task} pour
qu'\emph{au plus une} requête soit en vol à la fois (les tirs suivants
sont court-circuités tant que la tâche précédente n'est pas terminée). Un
\texttt{done\_callback} libère la référence pour éviter toute fuite. Lors
de l'arrêt, \texttt{cancel\_pending\_refresh()} attend la fin de la
requête en cours pendant un court délai avant de la couper.

%------------------------------------------------------------------
\section{Capteur tactile et interruption}
%------------------------------------------------------------------

Un capteur tactile capacitif est câblé sur le GPIO BCM~17 par défaut.
\texttt{TouchSensorService} utilise \texttt{gpiozero} (fallback
\texttt{RPi.GPIO}) et publie l'événement sur un
\texttt{asyncio.Event} via \texttt{loop.call\_soon\_threadsafe()}. La
boucle principale attend simultanément \emph{trois} événements :
fin du comportement courant, signal d'arrêt et toucher.

Lorsque le touch déclenche en premier, \texttt{\_handle\_touch\_interrupt}
est exécuté :
\begin{enumerate}[noitemsep]
	\item \texttt{motion.request\_abort()} pour couper toute sleep
	d'attente moteur ;
	\item \texttt{behavior\_task.cancel()} pour arrêter la conversation ;
	\item \texttt{audio\_output.stop\_playback()} et \texttt{motion.stop()}
	en parallèle ;
	\item \texttt{kill\_tracked\_subprocesses(grace\_s=0.25)} pour libérer
	sox/paplay/rpicam restés actifs ;
	\item \texttt{display.set\_expression(HAPPY)} puis lecture du WAV de
	rire (ou \texttt{speech.speak} en fallback).
\end{enumerate}

Une fois la réaction terminée, une nouvelle \texttt{behavior\_task} est
créée et la boucle reprend. Cela permet d'\textbf{interrompre} une réponse
en cours sans laisser de processus enfants orphelins.

\IfFileExists{public/koda-cycle4-touch-interruption.png}{%
	\begin{figure}[htbp]
		\centering
		\includegraphics[width=0.98\textwidth]{public/koda-cycle4-touch-interruption.png}
		\caption{Cycle~4 --- séquence d'interruption par capteur tactile (chatouilles)}
		\label{fig:ch4-touch-interruption}
	\end{figure}
}{}

%------------------------------------------------------------------
\section{Robustesse, registre de sous-processus et arrêt propre}
%------------------------------------------------------------------

La robustesse du logiciel embarqué repose sur plusieurs choix :
\begin{itemize}
	\item \textbf{Asynchronisme strict} : les lectures audio, appels HTTP,
	commandes série et lectures vidéo sont orchestrés par
	\texttt{asyncio}, sans thread bloquant. Les appels bloquants
	inévitables (\texttt{sox}, \texttt{serial.write}, ouverture USB) sont
	déportés via \texttt{asyncio.to\_thread} sur un
	\texttt{ThreadPoolExecutor} dédié.
	\item \textbf{Verrous locaux} : \texttt{DisplayService} et
	\texttt{MotionService} protègent leurs ressources série respectives
	contre les accès concurrents. Le \texttt{MotionService} ne tient jamais
	son verrou pendant un \texttt{sleep} d'attente moteur — règle
	cardinale pour ne pas geler le reste de la boucle.
	\item \textbf{Reprise sur crash} : la boucle principale extrait chaque
	itération dans \texttt{\_wake\_word\_iteration} ; toute exception (Vosk
	qui crashe, WebSocket Azure qui se ferme, USB qui se déconnecte) est
	loguée puis suivie d'une attente de 2~s avant la prochaine tentative.
	Le robot ne meurt jamais sur un \textsc{stack trace}.
	\item \textbf{Registre de sous-processus}
	(\texttt{utils/subprocess\_registry.py}) : tout
	\texttt{subprocess.Popen} suspect (sox, arecord, paplay, rpicam,
	yt-dlp) est créé avec \texttt{start\_new\_session=True} et enregistré.
	À l'arrêt, \texttt{kill\_tracked\_subprocesses()} envoie un
	\texttt{SIGTERM} puis un \texttt{SIGKILL} sur le \emph{groupe de
	processus} (via \texttt{os.killpg}) ; un \texttt{pkill\_orphans()}
	balaie ensuite les binaires connus pour rattraper les fuites
	éventuelles.
	\item \textbf{Logs structurés} : \texttt{utils/logger.py} configure un
	\texttt{RotatingFileHandler} avec horodatage millisecondes, ce qui
	permet de corréler une trace Pi avec une trace backend lors d'un bug
	transitoire.
	\item \textbf{Diagnostics explicites} : les composants absents sont
	loggués avec leur nom et leur message d'erreur, et listés au début de
	chaque démarrage (« 5/7 components detected »).
	\item \textbf{Arrêt propre} : sur \texttt{SIGINT} ou \texttt{SIGTERM},
	le robot affiche \texttt{SLEEPING}, arrête les moteurs, annule la
	tâche de rafraîchissement faciale en cours, tue les sous-processus
	tracés, ferme le client HTTP et libère les ports série.
\end{itemize}

%------------------------------------------------------------------
\section{Tests et validation logicielle}
%------------------------------------------------------------------

La validation du Cycle~4 combine tests automatisés Pytest et essais
réels sur le Raspberry Pi.

\begin{table}[H]
	\centering
	\caption{Tests de validation du logiciel Raspberry Pi}
	\label{tab:ch4-tests-logiciel}
	\renewcommand{\arraystretch}{1.25}
	\begin{tabularx}{\textwidth}{|>{\raggedright\arraybackslash}p{3.4cm}|>{\raggedright\arraybackslash}X|>{\raggedright\arraybackslash}p{3.4cm}|}
		\hline
		\textbf{Type de test} & \textbf{Procédure} & \textbf{Critère OK} \\
		\hline
		Configuration & \texttt{pytest tests/test\_config.py} avec defaults et overrides & Toutes valeurs chargées \\
		\hline
		Imports & \texttt{pytest tests/test\_imports.py} & Tous les modules importables \\
		\hline
		Hardware checks & \texttt{python -m services.hardware\_check} sur le Pi & Rapport composant par composant \\
		\hline
		Mot de réveil & Prononcer le mot devant le ReSpeaker en mode hybride & Vosk déclenche, Azure confirme, \textsc{WAKE} \\
		\hline
		VAD question & Poser une question puis se taire & WAV complet jusqu'au silence (pas 44 octets) \\
		\hline
		Backend action & Envoyer une question vocale & \texttt{ActionResult} reçu avec type valide \\
		\hline
		Rotation MPU6050 & \texttt{pytest tests/test\_motion\_concurrent.py} (7 cas) & Protocole \texttt{Rxxx}, DONE/ERR, deadband \\
		\hline
		WebSocket wake-word & \texttt{python tests/test\_ws\_wake\_word.py respeaker} & Trames PCM streamées, match reçu \\
		\hline
		Face refresh & \texttt{pytest tests/test\_face\_recognition\_lifecycle.py} & Au plus 1 task en vol, cancel propre \\
		\hline
		Touch interrupt & Toucher le capteur pendant une réponse & Audio coupé, sox tué, rire joué \\
		\hline
		Shutdown & \texttt{Ctrl+C} ou \texttt{SIGTERM} & Moteurs arrêtés, ports fermés, 0 zombie \\
		\hline
	\end{tabularx}
\end{table}

Les commandes minimales de validation logicielle sont :

\begin{lstlisting}[style=kodatest, language=shellkoda, caption={Commandes de validation du Cycle 4}]
pytest tests/                                  # suite unitaire complete
python tests/test_ws_wake_word.py respeaker    # smoke test WebSocket
python tests/test_mic_configs.py               # 6 configs micro + RMS
python -m app.main                             # essai bout-en-bout
\end{lstlisting}

%------------------------------------------------------------------
\section{Limites et perspectives}
%------------------------------------------------------------------

Le logiciel embarqué actuel assure le lien principal entre l'utilisateur, le
mouvement, l'affichage et le backend. Certaines améliorations restent
toutefois possibles :
\begin{itemize}
	\item streamer la STT côté Pi pendant la question pour économiser
	3--5~s par tour (le backend reçoit aujourd'hui le WAV complet) ;
	\item ajouter un service \texttt{systemd} pour démarrer KODA
	automatiquement au boot avec un \emph{watchdog} sur le port Arduino ;
	\item enrichir la télémétrie (erreurs audio, latences backend,
	rotations en échec) et la pousser vers Supabase pour le suivi des
	démonstrations ;
	\item stocker localement quelques réponses de secours si le backend
	devient temporairement indisponible ;
	\item permettre la découverte automatique du backend par mDNS comme
	fallback à \texttt{BACKEND\_URL}.
\end{itemize}

%------------------------------------------------------------------
\section{Conclusion}
%------------------------------------------------------------------

Ce chapitre a présenté le logiciel embarqué Raspberry Pi qui donne vie au
prototype KODA. Le programme \texttt{app.main} coordonne les services et
adaptateurs nécessaires pour passer d'une plateforme matérielle assemblée
à un compagnon capable d'écouter, de s'orienter au degré près grâce au
gyroscope MPU6050, de parler, d'afficher des émotions, de réagir au
toucher et d'exécuter cinq familles d'actions issues du backend.

Le choix d'une architecture asynchrone, séparée en services et
adaptateurs, rend le système maintenable et robuste face aux contraintes
du réel : matériel parfois absent, latence réseau, capture audio continue,
sous-processus à surveiller, ports série partagés et arrêt propre. Le
Cycle~4 complète ainsi le Cycle~3 en transformant le corps matériel en
plateforme interactive connectée au cerveau n8n et au Distributeur de
Services.

\begin{tcolorbox}[colback=blue!5!white, colframe=blue!60!black,
	title=\textbf{Points clés du Cycle 4}]
	\begin{itemize}[noitemsep]
		\item Démarrage \emph{parallèle} (\texttt{asyncio.gather}) avec mode dégradé contrôlé par \texttt{return\_exceptions=True}
		\item Architecture Python asynchrone en couches : services métier + adaptateurs matériels
		\item Mot de réveil hybride Vosk (gate local) + Azure WebSocket (confirmation)
		\item Rotation \emph{closed-loop} MPU6050 sur Arduino — précision $\pm$2$^\circ$
		\item Capteur tactile avec interruption asynchrone et réaction « chatouilles »
		\item Reconnaissance faciale en cache, rafraîchie en arrière-plan (fire-and-forget tracé)
		\item Dispatch des cinq types d'actions n8n (texte, musique, mouvement, sommeil, erreur)
		\item Registre de sous-processus + \texttt{killpg} + logs rotatifs pour un arrêt propre
	\end{itemize}
\end{tcolorbox}

Le chapitre suivant, \textbf{Cycle~5}, sera consacré à l'application
mobile cross-plateforme KodaMate, qui permet à l'utilisateur de
configurer, contrôler et superviser son compagnon.
"""


def main() -> int:
    raw = TEX.read_bytes()
    s_idx = raw.find(START_MARK)
    if s_idx < 0:
        print("ERROR: start mark not found", file=sys.stderr)
        return 1
    e_idx = raw.find(END_MARK, s_idx + len(START_MARK))
    if e_idx < 0:
        print("ERROR: end mark not found", file=sys.stderr)
        return 1

    # Walk back from e_idx to drop blank lines and the trailing `%====` banner
    # that introduces Cycle 5 — we want to keep everything up to (and not
    # including) that banner. Cycle 5 is introduced by the comment block:
    #   %===...
    #   % CHAPITRE VII : Cycle 5 ...
    #   %===...
    #   \chapter{Cycle 5 ...}
    # so we just rewind to the first %=== before END_MARK.
    banner = b"%=================================================================="
    banner_idx = raw.rfind(banner, s_idx, e_idx)
    if banner_idx < 0:
        # Fall back to e_idx (will simply leave \chapter directly after).
        replace_end = e_idx
    else:
        replace_end = banner_idx

    indented = _indent_with_tabs(NEW_CHAPTER).encode("utf-8")
    new_raw = raw[:s_idx] + indented + raw[replace_end:]

    TEX.write_bytes(new_raw)
    print(f"Cycle 4 rewritten: {len(NEW_CHAPTER):,} -> {len(indented):,} bytes "
          f"(replaced range {s_idx}..{replace_end})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
