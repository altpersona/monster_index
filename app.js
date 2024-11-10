const app = Vue.createApp({
    data() {
        return {
            selectedFile: ['underworld_monsterindex.json', 'The Proving Grounds of the Mad Overlord 203b_monsterindex.json'],
            files: ['underworld_monsterindex.json', 'The Proving Grounds of the Mad Overlord 203b_monsterindex.json', 'Option 3'],
            monsters: [],
            categories: {
                Name: new Set(),
                Str: new Set(),
                Con: new Set(),
                Dex: new Set(),
                ChallengeRating: new Set()
            },
            selectedFilters: {
                Name: '',
                Str: '',
                Con: '',
                Dex: '',
                ChallengeRating: ''
            },
            filteredMonsters: []
        };
    },
    methods: {
        loadFile() {
            fetch(this.selectedFile)
                .then(response => response.json())
                .then(data => {
                    this.monsters = data;
                    this.updateCategories();
                    this.filterMonsters();
                });
        },
        updateCategories() {
            this.categories = {
                Name: new Set(),
                Str: new Set(),
                Con: new Set(),
                Dex: new Set(),
                ChallengeRating: new Set()
            };

            this.monsters.forEach(monster => {
                this.categories.Name.add(monster.Name);
                this.categories.Str.add(monster.Str);
                this.categories.Con.add(monster.Con);
                this.categories.Dex.add(monster.Dex);
                this.categories.ChallengeRating.add(monster.ChallengeRating);
            });

            for (let key in this.categories) {
                this.categories[key] = Array.from(this.categories[key]);
            }
        },
        filterMonsters() {
            this.filteredMonsters = this.monsters.filter(monster => {
                return Object.keys(this.selectedFilters).every(key => {
                    return this.selectedFilters[key] === '' || monster[key] == this.selectedFilters[key];
                });
            });
        }
    },
    mounted() {
        this.loadFile();
    }
});

app.mount('#app');
