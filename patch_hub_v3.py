import sys

def run():
    with open('Component_1_Master_Hub.html', 'r', encoding='utf-8') as f:
        c = f.read()

    # 1. Add 'getDoc' to Firebase imports if not present
    if 'getDoc' not in c and 'setDoc' in c:
        c = c.replace('setDoc } from', 'setDoc, getDoc } from')
        
    # 2. Inject the Cloud Card in Overview Tab
    # Look for the ending </div> of the stats grid in overview tab, around line 155
    ov_old = """                     </div>
                </div>
                
                <div class="glass-panel p-6 border-red-200 border-2">"""
                
    ov_new = """                     </div>
                </div>
                
                <!-- NEW CLOUD SYNC CARD -->
                <div class="glass-panel p-6 border-t-4 border-blue-500 bg-white">
                    <h3 class="text-xl font-black text-slate-800 mb-2 flex items-center gap-2">
                        <svg class="w-6 h-6 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 15a4 4 0 004 4h9a5 5 0 10-.1-9.999 5.002 5.002 0 10-9.78 2.096A4.001 4.001 0 003 15z"></path></svg>
                        Global Cloud Synchronization
                    </h3>
                    <p class="text-sm text-gray-500 mb-6">Backup your active seating configurations to the secure Firebase cloud framework. This enables you to log into any other computer globally, click 'Restore', and instantly pick up where you left off!</p>
                    
                    <div class="flex flex-wrap gap-4">
                        <button @click="pushToCloud" class="bg-blue-600 hover:bg-blue-700 text-white font-bold py-3 px-6 rounded-lg shadow-sm transition flex items-center gap-2">
                            Push Schedule to Cloud
                        </button>
                        <button @click="pullFromCloud" class="bg-indigo-100 hover:bg-indigo-200 text-indigo-700 font-bold py-3 px-6 rounded-lg shadow-sm transition flex items-center gap-2 border border-indigo-300">
                            Restore from Cloud
                        </button>
                    </div>
                    <div v-show="cloudStatus" class="mt-4 text-sm font-bold text-blue-700 p-2 bg-blue-50 rounded border border-blue-100 inline-block">
                        {{ cloudStatus }}
                    </div>
                </div>
                
                <div class="glass-panel p-6 border-red-200 border-2">"""
    
    if ov_old in c:
        c = c.replace(ov_old, ov_new)
        
    # 3. Add Vue Data Variable
    data_old = \"\"\"            resetRegNo: '',
            resetStatus: '',\"\"\"
    
    data_new = \"\"\"            resetRegNo: '',
            resetStatus: '',
            cloudStatus: '',\"\"\"
    c = c.replace(data_old, data_new)
    
    # 4. Add the Vue API Methods (window.fsDb exposed below)
    method_old = """        clearDataCache() {"""
    
    method_new = """        async pushToCloud() {
            if(this.allocatedStudents.length === 0 && this.rawExtractedClasses.length === 0) {
                this.cloudStatus = '⚠️ Cannot push empty data to cloud.'; return;
            }
            this.cloudStatus = 'Uploading to Firebase...';
            try {
                let payload = {
                    customLabs: this.customLabs,
                    rawExtractedClasses: this.rawExtractedClasses,
                    allocatedStudents: this.allocatedStudents,
                    settings: this.settings,
                    websiteTimetable: this.websiteTimetable
                };
                await window.fsSetDoc(window.fsDoc(window.fsDb, 'exam_operations', 'core_state'), payload);
                this.cloudStatus = '✅ Successfully securely mirrored to Firebase Cloud! You can now load this on any computer.';
                setTimeout(() => this.cloudStatus='', 6000);
            } catch(e) {
                console.error(e);
                this.cloudStatus = '❌ Cloud Push Failed: ' + e.message;
            }
        },
        async pullFromCloud() {
            this.cloudStatus = 'Downloading from Firebase securely...';
            try {
                const snap = await window.fsGetDoc(window.fsDoc(window.fsDb, 'exam_operations', 'core_state'));
                if(snap.exists()) {
                    let d = snap.data();
                    if(d.customLabs) this.customLabs = d.customLabs;
                    if(d.rawExtractedClasses) this.rawExtractedClasses = d.rawExtractedClasses;
                    if(d.allocatedStudents) this.allocatedStudents = d.allocatedStudents;
                    if(d.settings) this.settings = d.settings;
                    if(d.websiteTimetable) this.websiteTimetable = d.websiteTimetable;
                    
                    this.cloudStatus = '✅ Global State Restored Successfully! Refreshing Engine...';
                    setTimeout(() => window.location.reload(), 2000);
                } else {
                    this.cloudStatus = '⚠️ No active cloud backup found for this portal.';
                }
            } catch(e) {
                console.error(e);
                this.cloudStatus = '❌ Cloud Pull Failed: ' + e.message;
            }
        },
        clearDataCache() {"""
        
    c = c.replace(method_old, method_new)
    
    # 5. Export Firebase globals so Vue can see them (since type="module" isolates imports)
    fs_old = """const firebaseApp = initializeApp(firebaseConfig);
const db = getFirestore(firebaseApp);

const { createApp } = Vue;"""

    fs_new = """const firebaseApp = initializeApp(firebaseConfig);
const db = getFirestore(firebaseApp);

// Export to window for Vue methods
window.fsDb = db;
window.fsSetDoc = setDoc;
window.fsDoc = doc;
window.fsGetDoc = getDoc;

const { createApp } = Vue;"""

    c = c.replace(fs_old, fs_new)

    with open('Component_1_Master_Hub.html', 'w', encoding='utf-8') as f:
        f.write(c)

run()
print('Firebase Manual Sync Module Integrated!')
