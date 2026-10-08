import sys

def run():
    with open('Component_1_Master_Hub.html', 'r', encoding='utf-8') as f:
        c = f.read()

    m_old = """    mounted() {
        onSnapshot(doc(db, 'exam_operations', 'core_state'), (docSnap) => {
            if (docSnap.exists()) {
                const d = docSnap.data();
                this.isSyncing = true;
                if(d.customLabs) this.customLabs = d.customLabs;
                if(d.rawExtractedClasses) this.rawExtractedClasses = d.rawExtractedClasses;
                if(d.allocatedStudents) this.allocatedStudents = d.allocatedStudents;
                if(d.rosterStats) this.rosterStats = d.rosterStats;
                if(d.settings) this.settings = d.settings;
                if(d.websiteTimetable) this.websiteTimetable = d.websiteTimetable;
                this.$nextTick(() => { this.isSyncing = false; });
            }
        });
    },"""

    m_new = """    mounted() {
        try {
            if(localStorage.getItem('jostel_classes')) this.rawExtractedClasses = JSON.parse(localStorage.getItem('jostel_classes'));
            if(localStorage.getItem('jostel_alloc')) this.allocatedStudents = JSON.parse(localStorage.getItem('jostel_alloc'));
            if(localStorage.getItem('jostel_labs')) this.customLabs = JSON.parse(localStorage.getItem('jostel_labs'));
            if(localStorage.getItem('jostel_settings')) this.settings = JSON.parse(localStorage.getItem('jostel_settings'));
            if(localStorage.getItem('jostel_stats')) this.rosterStats = JSON.parse(localStorage.getItem('jostel_stats'));
            
            if(this.allocatedStudents.length > 0) {
                this.validationErrors = [{ type: 'success', msg: 'Previous exam seating state recovered flawlessly from browser cache.' }];
            }
        } catch(e) {
            console.error('State Hydration Failed', e);
        }
    },
    watch: {
        rawExtractedClasses: { deep: true, handler(val) { localStorage.setItem('jostel_classes', JSON.stringify(val)); } },
        allocatedStudents: { deep: true, handler(val) { localStorage.setItem('jostel_alloc', JSON.stringify(val)); } },
        customLabs: { deep: true, handler(val) { localStorage.setItem('jostel_labs', JSON.stringify(val)); } },
        settings: { deep: true, handler(val) { localStorage.setItem('jostel_settings', JSON.stringify(val)); } },
        rosterStats: { deep: true, handler(val) { localStorage.setItem('jostel_stats', JSON.stringify(val)); } }
    },"""

    c = c.replace(m_old, m_new)

    col_old = """                tableData.push([
                    level,
                    cName,
                    firstRecord.Date,
                    firstRecord.Timing,
                    classGroups[cName].length + " Students"
                ]);"""
    col_new = """                let assignedLabs = [...new Set(classGroups[cName].map(s => s['Lab Room']))].join(', ');
                tableData.push([
                    level,
                    cName,
                    firstRecord.Date,
                    firstRecord.Timing,
                    assignedLabs,
                    classGroups[cName].length + " Students"
                ]);"""
    c = c.replace(col_old, col_new)

    h_old = "head: [['Academic Level', 'Department / Class Name', 'Exam Date', 'Scheduled Timing', 'Strength']],"
    h_new = "head: [['Academic Level', 'Department / Class Name', 'Exam Date', 'Scheduled Timing', 'Assigned Lab(s)', 'Strength']],"
    c = c.replace(h_old, h_new)

    with open('Component_1_Master_Hub.html', 'w', encoding='utf-8') as f:
        f.write(c)

run()
print('Patched successfully!')
