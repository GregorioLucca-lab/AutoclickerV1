# AutoclickerV1
Questo applicativo è un sistema di automazione basato sul riconoscimento immagini (Template Matching). Il suo scopo è monitorare costantemente fino a 5 zone specifiche dello schermo e, quando riconosce una determinata immagine (ad esempio un pulsante, un messaggio di gioco o un'icona), esegue automaticamente una sequenza di tasti.

Le funzionalità principali includono:

    Interfaccia Grafica (GUI): Un pannello di controllo scuro per configurare fino a 5 zone indipendenti.

    Configurazione Visiva: Permette di disegnare un rettangolo sullo schermo per definire l'area di ricerca e di caricare un'immagine di riferimento ("Template") da cercare in quell'area.

    Logica Intelligente (Keywords): Il programma cambia comportamento in base al nome che assegni alla zona (Label):

        Se il nome contiene "rigioca": Esegue una sequenza specifica (spesso usata per riavviare partite/livelli).

        Se il nome contiene "ingresso": Esegue una sequenza di entrata.

        Standard: Esegue una sequenza generica di movimento/azione.

    Input Diretto: Utilizza la libreria pydirectinput per simulare la pressione dei tasti a livello di driver, essenziale per far funzionare i comandi  (dove pyautogui spesso fallisce).


Il codice utilizza diverse librerie esterne che non sono incluse nell'installazione base di Python. Per utilizzare il programma, dovrà aprire il terminale (Prompt dei Comandi o PowerShell) ed eseguire il seguente comando:

pip install opencv-python numpy pyautogui pydirectinput pillow

