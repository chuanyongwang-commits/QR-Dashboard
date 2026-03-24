const { createApp, ref, computed, watch, onMounted } = Vue;

createApp({
    setup() {
        const fullData = ref([]);
        const uniqueAreas = ref([]);
        const uniqueScopes = ref([]);
        const uniqueOwners = ref([]);

        const filters = ref({ searchText: '', status: '', area: '', scope: '', owner: '' });
        const currentPage = ref(1);
        const pageSize = 15;
        const sortAsc = ref(false);
        const currentSortBy = ref('qr_number'); 

        // Modal for Adding Case
        const isModalOpen = ref(false);
        const newCase = ref({ title: '', trigger_area: '', scope: '', trigger_date: '', qr_owner: '', qr_status: 'Ongoing' });

        // Lightbox for Picture preview
        const lightbox = ref({ active: false, url: '' });

        onMounted(() => {
            fetch('/api/filters')
                .then(r => r.json())
                .then(data => {
                     uniqueAreas.value = data.areas;
                     uniqueScopes.value = data.scopes;
                     uniqueOwners.value = data.owners;
                });

            loadData();
        });

        function loadData() {
             const params = new URLSearchParams();
             if (filters.value.searchText) params.append('search', filters.value.searchText);
             if (filters.value.status) params.append('status', filters.value.status);
             if (filters.value.area) params.append('area', filters.value.area);
             if (filters.value.scope) params.append('scope', filters.value.scope);
             if (filters.value.owner) params.append('owner', filters.value.owner);
             params.append('sortAsc', sortAsc.value);
             params.append('sortBy', currentSortBy.value);

             fetch(`/api/cases?${params.toString()}`)
                 .then(r => r.json())
                 .then(data => {
                      fullData.value = data;
                 });
        }

        function changeSort(column) {
             if (currentSortBy.value === column) {
                  sortAsc.value = !sortAsc.value;
             } else {
                  currentSortBy.value = column;
                  sortAsc.value = false; 
             }
             loadData();
        }

        watch(filters, () => {
             currentPage.value = 1;
             loadData();
        }, { deep: true });

        const filteredData = computed(() => fullData.value);

        const maxPage = computed(() => Math.ceil(filteredData.value.length / pageSize));
        const paginatedData = computed(() => {
             const start = (currentPage.value - 1) * pageSize;
             return filteredData.value.slice(start, start + pageSize);
        });

        const paginationStart = computed(() => filteredData.value.length > 0 ? (currentPage.value - 1) * pageSize + 1 : 0);
        const paginationEnd = computed(() => Math.min(currentPage.value * pageSize, filteredData.value.length));

        function prevPage() { if (currentPage.value > 1) currentPage.value--; }
        function nextPage() { if (currentPage.value < maxPage.value) currentPage.value++; }

        function openLightbox(url) {
             lightbox.value = { active: true, url: url };
        }

        function submitNewCase() {
             fetch('/api/cases', {
                 method: 'POST',
                 headers: { 'Content-Type': 'application/json' },
                 body: JSON.stringify(newCase.value)
             })
             .then(r => r.json())
             .then(data => {
                  if (data.message) {
                       alert('Case added successfully with QR Support ID: #' + data.qr_number);
                       isModalOpen.value = false;
                       newCase.value = { title: '', trigger_area: '', scope: '', trigger_date: '', qr_owner: '', qr_status: 'Ongoing' };
                       loadData();
                  } else {
                       alert('Error: ' + JSON.stringify(data));
                  }
             })
             .catch(err => alert('Error adding case: ' + err));
        }

        return {
            filters,
            filteredData,
            currentPage,
            pageSize,
            sortAsc,
            currentSortBy,
            uniqueAreas, uniqueScopes, uniqueOwners,
            paginatedData, maxPage, paginationStart, paginationEnd,
            prevPage, nextPage, changeSort,
            isModalOpen, newCase, submitNewCase,
            lightbox, openLightbox
        };
    }
}).mount('#app');
