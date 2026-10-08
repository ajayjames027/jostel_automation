import sys

def run():
    with open('Component_1_Master_Hub.html', 'r', encoding='utf-8') as f:
        c = f.read()

    # 1. Add Help Desk tab into Sidebar (around line 117)
    sb_old = """            <div class="sidebar-item" :class="{'active': activeTab === 'live'}" @click="activeTab = 'live'">
                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"></path></svg>
                Live Control Panel
            </div>"""
    
    sb_new = """            <div class="sidebar-item" :class="{'active': activeTab === 'live'}" @click="activeTab = 'live'">
                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"></path></svg>
                Live Control Panel
            </div>
            
            <div class="sidebar-item" :class="{'active': activeTab === 'helpdesk'}" @click="activeTab = 'helpdesk'">
                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M18.364 5.636l-3.536 3.536m0 5.656l3.536 3.536M9.172 9.172L5.636 5.636m3.536 9.192l-3.536 3.536M21 12a9 9 0 11-18 0 9 9 0 0118 0zm-5 0a4 4 0 11-8 0 4 4 0 018 0z"></path></svg>
                Student Help Desk
            </div>"""
    c = c.replace(sb_old, sb_new)

    # 2. Add Help Desk HTML Panel Template right before STUB TABS
    panel_old = """            <!-- STUB TABS -->"""
    panel_new = """            <!-- HELPDESK TAB -->
            <div v-show="activeTab === 'helpdesk'" class="space-y-6 max-w-4xl mx-auto pb-20 h-full">
                <div>
                    <h2 class="text-2xl font-bold text-slate-800">Student Help Desk Console</h2>
                    <p class="text-slate-500 text-sm">Real-time emergency operational commands during live exams.</p>
                </div>
                
                <div class="glass-panel p-8 bg-white border-l-4 border-rose-500 shadow-sm relative overflow-hidden">
                    <h3 class="text-xl font-black text-gray-800 mb-2 mt-2">Force Password Reset API</h3>
                    <p class="text-sm text-gray-600 mb-6">Instantly force a student's cloud portal password to reset to <code>12345</code> and mandate a security rotation on their next login bypass.</p>
                    
                    <div class="flex gap-4">
                        <input type="text" v-model="resetRegNo" class="w-full md:w-auto bg-gray-50 border border-gray-300 text-gray-900 font-bold px-4 py-3 rounded-lg focus:ring-rose-500 focus:border-rose-500 block" placeholder="e.g. 26UCO34">
                        <button @click="triggerPasswordReset" :disabled="!resetRegNo" class="bg-rose-500 hover:bg-rose-600 disabled:opacity-50 text-white font-bold py-3 px-8 rounded-lg shadow-sm transition flex items-center gap-2">
                            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"></path></svg>
                            Execute Reset
                        </button>
                    </div>
                </div>
            </div>

            <!-- STUB TABS -->"""
    c = c.replace(panel_old, panel_new)

    # 3. Add Exam Name to the UI near Target Start Date
    ui_old = """                            <div>
                                <label class="text-[10px] font-bold text-gray-500 block mb-1 uppercase">Target Start Date</label>
                                <input type="date" v-model="settings.startDate" class="text-sm font-semibold p-1 border rounded bg-white w-36">
                            </div>"""
    ui_new = """                            <div>
                                <label class="text-[10px] font-bold text-gray-500 block mb-1 uppercase">Exam Target Name</label>
                                <input type="text" v-model="websiteTimetable.examType" class="text-sm font-bold p-1 border rounded bg-white w-32 text-primary" placeholder="e.g. Component I">
                            </div>
                            <div>
                                <label class="text-[10px] font-bold text-gray-500 block mb-1 uppercase">Target Start Date</label>
                                <input type="date" v-model="settings.startDate" class="text-sm font-semibold p-1 border rounded bg-white w-36">
                            </div>"""
    c = c.replace(ui_old, ui_new)
    
    # 4. Bind the Exam Name correctly inside exportPublicTimetablePDF()
    pdf_old = """            doc.text(`Exam Type: ${examTitle.toUpperCase()}`, 105, 30, { align: "center" });"""
    pdf_new = """            doc.text(`Exam Type: ${this.websiteTimetable.examType.toUpperCase()}`, 105, 30, { align: "center" });"""
    c = c.replace(pdf_old, pdf_new)

    pdf_old2 = """            doc.text("Component I - Computer Based Test", 105, 27, { align: "center" });"""
    pdf_new2 = """            doc.text(`${this.websiteTimetable.examType || 'Component I'} - Computer Based Test`, 105, 27, { align: "center" });"""
    c = c.replace(pdf_old2, pdf_new2)

    # 5. Add Vue Data variable and Method
    vue_data_old = """            claimForm: { name: '', sessions: 1, rate: 250 },"""
    vue_data_new = """            claimForm: { name: '', sessions: 1, rate: 250 },
            resetRegNo: '','""
            resetStatus: '',"""
    c = c.replace(vue_data_old, vue_data_new)
    
    # 6. Add method
    vue_method_old = """        clearDataCache() {"""
    vue_method_new = """        triggerPasswordReset() {
            if(!this.resetRegNo) return;
            alert(`For security, API CORS strictly prohibits pure frontend Moodle Database connections here.\n\nPlease open your Terminal and run:\npython Password_Reset_Bot.py\n\nThe AI has engineered a specific bot dedicated to resetting ${this.resetRegNo}'s password offline safely!`);
        },
        clearDataCache() {"""
    c = c.replace(vue_method_old, vue_method_new)

    with open('Component_1_Master_Hub.html', 'w', encoding='utf-8') as f:
        f.write(c)

run()
print('Patched strictly next to Target Start Date!')
