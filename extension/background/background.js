/*
 * Ce code applique le Plan V5 du projet de tri d’emails LLM.
 * Conformité RGPD : Aucune donnée stockée en local storage extension.
 */

const NATIVE_APP_NAME = "com.mailsorter.backend";
const client = new window.NativeClient(NATIVE_APP_NAME);

// Initialisation
client.connect();

// Écoute des réponses du backend
window.addEventListener('native-response', async (e) => {
    const response = e.detail;
    
    if (response.action === 'move' && response.target) {
        try {
            await moveMessage(response.id, response.target);
        } catch (err) {
            console.error(`Failed to move message ${response.id}:`, err);
        }
    }
});

// Écoute des nouveaux emails
browser.messages.onNewMailReceived.addListener(async (folder, messages) => {
    console.log(`New mail received in ${folder.name}`);
    
    for (let message of messages.messages) {
        // On ignore les messages déjà lus ou marqués (optionnel)
        if (message.read) continue;

        try {
            await processMessage(message);
        } catch (err) {
            console.error(`Error processing message ${message.id}:`, err);
        }
    }
});

async function processMessage(messageHeader) {
    // 1. Récupérer le corps du message
    // Note: getFull peut être lourd, on pourrait utiliser get(id) et parser
    // Pour l'instant on utilise une méthode hypothétique simplifiée ou on se base sur le subject
    // TODO: Vérifier l'API exacte pour récupérer le body text only (pas le HTML complet)
    // browser.messages.getFull(messageHeader.id) retourne un MessagePart
    
    let bodySnippet = "Body preview unavailable";
    try {
        const fullMessage = await browser.messages.getFull(messageHeader.id);
        // Simplification: on prend juste le sujet pour l'instant si le body est trop complexe à parser sans lib externe
        // Dans une V2, on ajoutera un parser MIME JS.
        if (fullMessage.body) {
             bodySnippet = fullMessage.body.substr(0, 500); // Pré-troncature
        }
    } catch (e) {
        console.warn("Could not fetch full body, using subject only.");
    }

    // 2. Récupérer la liste des dossiers du compte
    const account = await browser.accounts.get(messageHeader.folder.accountId);
    const folders = await getAllFolders(account);
    const folderNames = folders.map(f => f.name).filter(n => n !== "Inbox" && n !== "Trash" && n !== "Sent");

    // 3. Envoyer au backend
    const payload = {
        type: "classify",
        payload: {
            id: messageHeader.id,
            subject: messageHeader.subject,
            body: bodySnippet,
            folders: folderNames
        }
    };

    client.sendMessage(payload);
}

async function moveMessage(messageId, targetFolderName) {
    // Il faut retrouver l'objet folder correspondant au nom
    // C'est inefficace de refaire ça à chaque fois, il faudrait un cache.
    // Pour ce POC, on re-parcourt.
    
    const msg = await browser.messages.get(messageId);
    const account = await browser.accounts.get(msg.folder.accountId);
    const folders = await getAllFolders(account);
    
    const targetFolder = folders.find(f => f.name === targetFolderName);
    
    if (targetFolder) {
        console.log(`Moving message ${messageId} to ${targetFolderName}`);
        await browser.messages.move([messageId], targetFolder);
    } else {
        console.warn(`Target folder '${targetFolderName}' not found.`);
    }
}

// Helper récursif pour lister les dossiers
async function getAllFolders(account) {
    let allFolders = [];
    
    async function traverse(folder) {
        allFolders.push(folder);
        if (folder.subFolders) {
            for (let sub of folder.subFolders) {
                await traverse(sub);
            }
        }
    }

    // rootFolder n'est pas toujours accessible directement selon l'API, 
    // parfois account.folders est la racine.
    // TODO: Vérifier compatibilité Betterbird vs Thunderbird
    if (account.folders) {
        for (let f of account.folders) {
            await traverse(f);
        }
    }
    
    return allFolders;
}
