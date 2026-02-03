// Recipe Hunter JavaScript

const API_BASE_URL = '/api';
const AUTH_TOKEN_KEY = 'auth_token';
const USERNAME_KEY = 'username';

// DOM Elements - Pantry
const pantryInput = document.getElementById('pantryInput');
const addPantryBtn = document.getElementById('addPantryBtn');
const pantryList = document.getElementById('pantryList');
const emptyPantry = document.getElementById('emptyPantry');

// DOM Elements - Vibe Search
const vibeInput = document.getElementById('vibeInput');
const vibeSearchBtn = document.getElementById('vibeSearchBtn');
const vibeSearchBtnText = document.getElementById('vibeSearchBtnText');
const vibeSearchBtnSpinner = document.getElementById('vibeSearchBtnSpinner');

// DOM Elements - Shopping List
const shoppingInput = document.getElementById('shoppingInput');
const addShoppingBtn = document.getElementById('addShoppingBtn');
const shoppingList = document.getElementById('shoppingList');
const emptyShopping = document.getElementById('emptyShopping');
const includePantry = document.getElementById('includePantry');
const shoppingRecipesBtn = document.getElementById('shoppingRecipesBtn');
const shoppingRecipesBtnText = document.getElementById('shoppingRecipesBtnText');
const shoppingRecipesBtnSpinner = document.getElementById('shoppingRecipesBtnSpinner');

// DOM Elements - Generate
const cuisineGrid = document.getElementById('cuisineGrid');
const recipeCount = document.getElementById('recipeCount');
const recipeCountDisplay = document.getElementById('recipeCountDisplay');
const generateBtn = document.getElementById('generateBtn');
const generateBtnText = document.getElementById('generateBtnText');
const generateBtnSpinner = document.getElementById('generateBtnSpinner');

// DOM Elements - Results
const recipesSection = document.getElementById('recipesSection');
const recipesGrid = document.getElementById('recipesGrid');
const loadingSection = document.getElementById('loadingSection');
const savedSection = document.getElementById('savedSection');
const savedCount = document.getElementById('savedCount');
const savedToggle = document.getElementById('savedToggle');
const savedRecipesList = document.getElementById('savedRecipesList');
const errorMessage = document.getElementById('errorMessage');

// State
let pantryItems = [];
let shoppingItems = [];
let savedRecipes = [];
let generatedRecipes = [];

// Cuisines (loaded from API or fallback)
const defaultCuisines = [
    'Italian', 'Chinese', 'Indian', 'American', 'Mexican',
    'Mediterranean', 'Japanese', 'Thai', 'French', 'Korean'
];

// ============================================
// Initialization
// ============================================

document.addEventListener('DOMContentLoaded', () => {
    checkAuthentication();
    initializeEventListeners();
    loadPantry();
    loadShoppingList();
    loadCuisines();
    loadSavedRecipes();
});

// ============================================
// Authentication
// ============================================

function checkAuthentication() {
    const token = localStorage.getItem(AUTH_TOKEN_KEY);
    if (!token) {
        window.location.href = '/login.html';
        return;
    }

    const username = localStorage.getItem(USERNAME_KEY);
    if (username) {
        document.getElementById('usernameDisplay').textContent = username;
    }
}

function logout() {
    localStorage.removeItem(AUTH_TOKEN_KEY);
    localStorage.removeItem(USERNAME_KEY);
    window.location.href = '/login.html';
}

function getAuthHeaders() {
    const token = localStorage.getItem(AUTH_TOKEN_KEY);
    return {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
    };
}

function handleAuthError() {
    localStorage.removeItem(AUTH_TOKEN_KEY);
    localStorage.removeItem(USERNAME_KEY);
    window.location.href = '/login.html';
}

// ============================================
// Event Listeners
// ============================================

function initializeEventListeners() {
    // Pantry
    addPantryBtn.addEventListener('click', addPantryItem);
    pantryInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            e.preventDefault();
            addPantryItem();
        }
    });

    // Shopping List
    addShoppingBtn.addEventListener('click', addShoppingItem);
    shoppingInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            e.preventDefault();
            addShoppingItem();
        }
    });
    shoppingRecipesBtn.addEventListener('click', generateFromShoppingList);

    // Vibe Search
    vibeSearchBtn.addEventListener('click', vibeSearch);
    vibeInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            vibeSearch();
        }
    });

    // Recipe count slider
    recipeCount.addEventListener('input', () => {
        recipeCountDisplay.textContent = recipeCount.value;
    });

    // Generate button
    generateBtn.addEventListener('click', generateRecipes);

    // Saved recipes toggle
    savedToggle.addEventListener('click', toggleSavedRecipes);
}

// ============================================
// Pantry Functions
// ============================================

async function loadPantry() {
    try {
        const response = await fetch(`${API_BASE_URL}/pantry`, {
            headers: getAuthHeaders()
        });

        if (response.status === 401) {
            handleAuthError();
            return;
        }

        if (!response.ok) throw new Error('Failed to load pantry');

        const data = await response.json();
        pantryItems = data.items || [];
        renderPantry();
    } catch (error) {
        console.error('Error loading pantry:', error);
    }
}

function renderPantry() {
    if (pantryItems.length === 0) {
        emptyPantry.style.display = 'block';
        pantryList.innerHTML = '';
        pantryList.appendChild(emptyPantry);
        return;
    }

    emptyPantry.style.display = 'none';
    pantryList.innerHTML = pantryItems.map(item => `
        <div class="pantry-item" data-id="${item.id}">
            <span class="pantry-item-name">${escapeHtml(item.item_name)}</span>
            <button class="pantry-item-remove" onclick="removePantryItem(${item.id})" title="Remove">
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <line x1="18" y1="6" x2="6" y2="18"></line>
                    <line x1="6" y1="6" x2="18" y2="18"></line>
                </svg>
            </button>
        </div>
    `).join('');
}

async function addPantryItem() {
    const itemName = pantryInput.value.trim();
    if (!itemName) return;

    try {
        const response = await fetch(`${API_BASE_URL}/pantry`, {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify({ item_name: itemName })
        });

        if (response.status === 401) {
            handleAuthError();
            return;
        }

        if (!response.ok) {
            const error = await response.json();
            showError(error.detail || 'Failed to add item');
            return;
        }

        const newItem = await response.json();
        pantryItems.push(newItem);
        pantryInput.value = '';
        renderPantry();
    } catch (error) {
        console.error('Error adding pantry item:', error);
        showError('Failed to add item');
    }
}

async function removePantryItem(itemId) {
    try {
        const response = await fetch(`${API_BASE_URL}/pantry/${itemId}`, {
            method: 'DELETE',
            headers: getAuthHeaders()
        });

        if (response.status === 401) {
            handleAuthError();
            return;
        }

        if (!response.ok) throw new Error('Failed to remove item');

        pantryItems = pantryItems.filter(item => item.id !== itemId);
        renderPantry();
    } catch (error) {
        console.error('Error removing pantry item:', error);
        showError('Failed to remove item');
    }
}

// ============================================
// Shopping List Functions
// ============================================

async function loadShoppingList() {
    try {
        const response = await fetch(`${API_BASE_URL}/shopping-list`, {
            headers: getAuthHeaders()
        });

        if (response.status === 401) {
            handleAuthError();
            return;
        }

        if (!response.ok) throw new Error('Failed to load shopping list');

        const data = await response.json();
        shoppingItems = data.items || [];
        renderShoppingList();
    } catch (error) {
        console.error('Error loading shopping list:', error);
    }
}

function renderShoppingList() {
    if (shoppingItems.length === 0) {
        emptyShopping.style.display = 'block';
        shoppingList.innerHTML = '';
        shoppingList.appendChild(emptyShopping);
        return;
    }

    emptyShopping.style.display = 'none';
    shoppingList.innerHTML = shoppingItems.map(item => `
        <div class="shopping-item" data-id="${item.id}">
            <span class="shopping-item-name">${escapeHtml(item.item_name)}</span>
            <button class="shopping-item-remove" onclick="removeShoppingItem(${item.id})" title="Remove">
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <line x1="18" y1="6" x2="6" y2="18"></line>
                    <line x1="6" y1="6" x2="18" y2="18"></line>
                </svg>
            </button>
        </div>
    `).join('');
}

async function addShoppingItem() {
    const itemName = shoppingInput.value.trim();
    if (!itemName) return;

    try {
        const response = await fetch(`${API_BASE_URL}/shopping-list`, {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify({ item_name: itemName })
        });

        if (response.status === 401) {
            handleAuthError();
            return;
        }

        if (!response.ok) {
            const error = await response.json();
            showError(error.detail || 'Failed to add item');
            return;
        }

        const newItem = await response.json();
        shoppingItems.push(newItem);
        shoppingInput.value = '';
        renderShoppingList();
    } catch (error) {
        console.error('Error adding shopping item:', error);
        showError('Failed to add item');
    }
}

async function removeShoppingItem(itemId) {
    try {
        const response = await fetch(`${API_BASE_URL}/shopping-list/${itemId}`, {
            method: 'DELETE',
            headers: getAuthHeaders()
        });

        if (response.status === 401) {
            handleAuthError();
            return;
        }

        if (!response.ok) throw new Error('Failed to remove item');

        shoppingItems = shoppingItems.filter(item => item.id !== itemId);
        renderShoppingList();
    } catch (error) {
        console.error('Error removing shopping item:', error);
        showError('Failed to remove item');
    }
}

async function generateFromShoppingList() {
    if (shoppingItems.length === 0) {
        showError('Please add some items to your shopping list first');
        return;
    }

    setShoppingLoading(true);
    recipesSection.style.display = 'none';
    loadingSection.style.display = 'block';
    hideError();

    try {
        const response = await fetch(`${API_BASE_URL}/recipes/from-shopping-list`, {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify({
                recipe_count: 3,
                include_pantry: includePantry.checked
            })
        });

        if (response.status === 401) {
            handleAuthError();
            return;
        }

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to generate recipes');
        }

        const data = await response.json();
        generatedRecipes = data.recipes || [];
        renderShoppingRecipes(data.shopping_list_used, data.pantry_used);
    } catch (error) {
        console.error('Error generating recipes from shopping list:', error);
        showError(error.message || 'Failed to generate recipes');
    } finally {
        setShoppingLoading(false);
        loadingSection.style.display = 'none';
    }
}

function renderShoppingRecipes(shoppingUsed, pantryUsed) {
    if (generatedRecipes.length === 0) {
        recipesSection.style.display = 'none';
        return;
    }

    recipesSection.style.display = 'block';
    recipesGrid.innerHTML = generatedRecipes.map((recipe, index) => `
        <div class="recipe-card" data-index="${index}">
            <div class="recipe-card-header">
                <h3 class="recipe-name">${escapeHtml(recipe.name)}</h3>
                <span class="recipe-cuisine-badge">${escapeHtml(recipe.cuisine)}</span>
            </div>
            <div class="recipe-time">${escapeHtml(recipe.prep_time || 'Time varies')}</div>

            <div class="recipe-ingredients">
                <p class="recipe-section-title">Ingredients</p>
                <ul class="ingredient-list">
                    ${(recipe.from_shopping_list || []).map(ing =>
                        `<li class="ingredient-from-shopping">
                            <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <circle cx="9" cy="21" r="1"></circle>
                                <circle cx="20" cy="21" r="1"></circle>
                                <path d="M1 1h4l2.68 13.39a2 2 0 0 0 2 1.61h9.72a2 2 0 0 0 2-1.61L23 6H6"></path>
                            </svg>
                            ${escapeHtml(ing)} (shopping list)
                        </li>`
                    ).join('')}
                    ${(recipe.from_pantry || []).map(ing =>
                        `<li class="ingredient-from-pantry">
                            <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <polyline points="20 6 9 17 4 12"></polyline>
                            </svg>
                            ${escapeHtml(ing)} (in pantry)
                        </li>`
                    ).join('')}
                    ${(recipe.additional_needed || []).map(ing =>
                        `<li class="ingredient-additional">
                            <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <line x1="12" y1="5" x2="12" y2="19"></line>
                                <line x1="5" y1="12" x2="19" y2="12"></line>
                            </svg>
                            ${escapeHtml(ing)} (extra needed)
                        </li>`
                    ).join('')}
                </ul>
            </div>

            <div class="recipe-instructions">
                <p class="recipe-section-title">Instructions</p>
                <ol class="instruction-list">
                    ${(recipe.instructions || []).map(step =>
                        `<li>${escapeHtml(step)}</li>`
                    ).join('')}
                </ol>
            </div>

            <div class="recipe-actions">
                <button class="btn btn-primary btn-save" onclick="saveRecipe(${index})">
                    Save Recipe
                </button>
            </div>
        </div>
    `).join('');
}

function setShoppingLoading(loading) {
    shoppingRecipesBtn.disabled = loading;
    shoppingRecipesBtnText.style.display = loading ? 'none' : 'inline';
    shoppingRecipesBtnSpinner.style.display = loading ? 'inline-block' : 'none';
}

// ============================================
// Vibe Search Functions
// ============================================

async function vibeSearch() {
    const vibe = vibeInput.value.trim();

    if (!vibe || vibe.length < 3) {
        showError('Please describe what you\'re craving (at least 3 characters)');
        return;
    }

    setVibeLoading(true);
    recipesSection.style.display = 'none';
    loadingSection.style.display = 'block';
    hideError();

    try {
        const response = await fetch(`${API_BASE_URL}/recipes/vibe-search`, {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify({
                vibe: vibe,
                recipe_count: 3
            })
        });

        if (response.status === 401) {
            handleAuthError();
            return;
        }

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to search recipes');
        }

        const data = await response.json();
        generatedRecipes = data.recipes || [];
        renderVibeRecipes();
    } catch (error) {
        console.error('Error in vibe search:', error);
        showError(error.message || 'Failed to search recipes');
    } finally {
        setVibeLoading(false);
        loadingSection.style.display = 'none';
    }
}

function renderVibeRecipes() {
    if (generatedRecipes.length === 0) {
        recipesSection.style.display = 'none';
        return;
    }

    recipesSection.style.display = 'block';
    recipesGrid.innerHTML = generatedRecipes.map((recipe, index) => `
        <div class="recipe-card" data-index="${index}">
            <div class="recipe-card-header">
                <h3 class="recipe-name">${escapeHtml(recipe.name)}</h3>
                <span class="recipe-cuisine-badge">${escapeHtml(recipe.cuisine)}</span>
            </div>
            <div class="recipe-time">${escapeHtml(recipe.prep_time || 'Time varies')}</div>

            <div class="recipe-ingredients">
                <p class="recipe-section-title">Ingredients</p>
                <ul class="ingredient-list">
                    ${(recipe.ingredients || []).map(ing =>
                        `<li class="ingredient-additional">
                            <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <polyline points="20 6 9 17 4 12"></polyline>
                            </svg>
                            ${escapeHtml(ing)}
                        </li>`
                    ).join('')}
                </ul>
            </div>

            <div class="recipe-instructions">
                <p class="recipe-section-title">Instructions</p>
                <ol class="instruction-list">
                    ${(recipe.instructions || []).map(step =>
                        `<li>${escapeHtml(step)}</li>`
                    ).join('')}
                </ol>
            </div>

            <div class="recipe-actions">
                <button class="btn btn-primary btn-save" onclick="saveVibeRecipe(${index})">
                    Save Recipe
                </button>
            </div>
        </div>
    `).join('');
}

function setVibeLoading(loading) {
    vibeSearchBtn.disabled = loading;
    vibeSearchBtnText.style.display = loading ? 'none' : 'inline';
    vibeSearchBtnSpinner.style.display = loading ? 'inline-block' : 'none';
}

async function saveVibeRecipe(index) {
    const recipe = generatedRecipes[index];
    if (!recipe) return;

    try {
        const response = await fetch(`${API_BASE_URL}/recipes/save`, {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify({
                recipe_name: recipe.name,
                cuisine: recipe.cuisine,
                ingredients: JSON.stringify(recipe.ingredients || []),
                instructions: JSON.stringify(recipe.instructions || []),
                prep_time: recipe.prep_time
            })
        });

        if (response.status === 401) {
            handleAuthError();
            return;
        }

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to save recipe');
        }

        const savedRecipe = await response.json();
        savedRecipes.unshift(savedRecipe);
        renderSavedRecipes();

        // Update button to show saved
        const btn = document.querySelector(`.recipe-card[data-index="${index}"] .btn-save`);
        if (btn) {
            btn.textContent = 'Saved!';
            btn.classList.add('btn-saved');
            btn.disabled = true;
        }
    } catch (error) {
        console.error('Error saving recipe:', error);
        showError(error.message || 'Failed to save recipe');
    }
}

// ============================================
// Cuisine Functions
// ============================================

async function loadCuisines() {
    try {
        const response = await fetch(`${API_BASE_URL}/cuisines`, {
            headers: getAuthHeaders()
        });

        if (response.ok) {
            const data = await response.json();
            renderCuisines(data.cuisines || defaultCuisines);
        } else {
            renderCuisines(defaultCuisines);
        }
    } catch (error) {
        console.error('Error loading cuisines:', error);
        renderCuisines(defaultCuisines);
    }
}

function renderCuisines(cuisines) {
    cuisineGrid.innerHTML = cuisines.map((cuisine, index) => `
        <div class="cuisine-option">
            <input type="checkbox" id="cuisine_${index}" value="${cuisine}" ${index < 2 ? 'checked' : ''}>
            <label for="cuisine_${index}">${cuisine}</label>
        </div>
    `).join('');
}

function getSelectedCuisines() {
    const checkboxes = cuisineGrid.querySelectorAll('input[type="checkbox"]:checked');
    return Array.from(checkboxes).map(cb => cb.value);
}

// ============================================
// Recipe Generation
// ============================================

async function generateRecipes() {
    const selectedCuisines = getSelectedCuisines();

    if (selectedCuisines.length === 0) {
        showError('Please select at least one cuisine');
        return;
    }

    if (pantryItems.length === 0) {
        showError('Please add some ingredients to your pantry first');
        return;
    }

    setLoading(true);
    recipesSection.style.display = 'none';
    loadingSection.style.display = 'block';
    hideError();

    try {
        const response = await fetch(`${API_BASE_URL}/recipes/generate`, {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify({
                cuisines: selectedCuisines,
                recipe_count: parseInt(recipeCount.value)
            })
        });

        if (response.status === 401) {
            handleAuthError();
            return;
        }

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to generate recipes');
        }

        const data = await response.json();
        generatedRecipes = data.recipes || [];
        renderRecipes();
    } catch (error) {
        console.error('Error generating recipes:', error);
        showError(error.message || 'Failed to generate recipes');
    } finally {
        setLoading(false);
        loadingSection.style.display = 'none';
    }
}

function renderRecipes() {
    if (generatedRecipes.length === 0) {
        recipesSection.style.display = 'none';
        return;
    }

    recipesSection.style.display = 'block';
    recipesGrid.innerHTML = generatedRecipes.map((recipe, index) => `
        <div class="recipe-card" data-index="${index}">
            <div class="recipe-card-header">
                <h3 class="recipe-name">${escapeHtml(recipe.name)}</h3>
                <span class="recipe-cuisine-badge">${escapeHtml(recipe.cuisine)}</span>
            </div>
            <div class="recipe-time">${escapeHtml(recipe.prep_time || 'Time varies')}</div>

            <div class="recipe-ingredients">
                <p class="recipe-section-title">Ingredients</p>
                <ul class="ingredient-list">
                    ${(recipe.ingredients_in_pantry || []).map(ing =>
                        `<li class="ingredient-in-pantry">
                            <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <polyline points="20 6 9 17 4 12"></polyline>
                            </svg>
                            ${escapeHtml(ing)} (in pantry)
                        </li>`
                    ).join('')}
                    ${(recipe.ingredients_to_buy || []).map(ing =>
                        `<li class="ingredient-to-buy">
                            <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <circle cx="9" cy="21" r="1"></circle>
                                <circle cx="20" cy="21" r="1"></circle>
                                <path d="M1 1h4l2.68 13.39a2 2 0 0 0 2 1.61h9.72a2 2 0 0 0 2-1.61L23 6H6"></path>
                            </svg>
                            ${escapeHtml(ing)} (to buy)
                        </li>`
                    ).join('')}
                </ul>
            </div>

            <div class="recipe-instructions">
                <p class="recipe-section-title">Instructions</p>
                <ol class="instruction-list">
                    ${(recipe.instructions || []).map(step =>
                        `<li>${escapeHtml(step)}</li>`
                    ).join('')}
                </ol>
            </div>

            <div class="recipe-actions">
                <button class="btn btn-primary btn-save" onclick="saveRecipe(${index})">
                    Save Recipe
                </button>
            </div>
        </div>
    `).join('');
}

// ============================================
// Saved Recipes
// ============================================

async function loadSavedRecipes() {
    try {
        const response = await fetch(`${API_BASE_URL}/recipes/saved`, {
            headers: getAuthHeaders()
        });

        if (response.status === 401) {
            handleAuthError();
            return;
        }

        if (!response.ok) throw new Error('Failed to load saved recipes');

        const data = await response.json();
        savedRecipes = data.recipes || [];
        renderSavedRecipes();
    } catch (error) {
        console.error('Error loading saved recipes:', error);
    }
}

function renderSavedRecipes() {
    savedCount.textContent = `(${savedRecipes.length})`;

    if (savedRecipes.length === 0) {
        savedRecipesList.innerHTML = '<p class="empty-pantry">No saved recipes yet</p>';
        return;
    }

    savedRecipesList.innerHTML = savedRecipes.map(recipe => `
        <div class="saved-recipe-item" data-id="${recipe.id}">
            <div class="saved-recipe-info">
                <span class="saved-recipe-name">${escapeHtml(recipe.recipe_name)}</span>
                ${recipe.cuisine ? `<span class="recipe-cuisine-badge">${escapeHtml(recipe.cuisine)}</span>` : ''}
            </div>
            <button class="pantry-item-remove" onclick="deleteSavedRecipe(${recipe.id})" title="Remove">
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <line x1="18" y1="6" x2="6" y2="18"></line>
                    <line x1="6" y1="6" x2="18" y2="18"></line>
                </svg>
            </button>
        </div>
    `).join('');
}

function toggleSavedRecipes() {
    const isVisible = savedRecipesList.classList.contains('visible');
    savedRecipesList.classList.toggle('visible');
    savedToggle.textContent = isVisible ? 'Show' : 'Hide';
}

async function saveRecipe(index) {
    const recipe = generatedRecipes[index];
    if (!recipe) return;

    try {
        const response = await fetch(`${API_BASE_URL}/recipes/save`, {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify({
                recipe_name: recipe.name,
                cuisine: recipe.cuisine,
                ingredients: JSON.stringify(recipe.ingredients || []),
                instructions: JSON.stringify(recipe.instructions || []),
                prep_time: recipe.prep_time
            })
        });

        if (response.status === 401) {
            handleAuthError();
            return;
        }

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to save recipe');
        }

        const savedRecipe = await response.json();
        savedRecipes.unshift(savedRecipe);
        renderSavedRecipes();

        // Update button to show saved
        const btn = document.querySelector(`.recipe-card[data-index="${index}"] .btn-save`);
        if (btn) {
            btn.textContent = 'Saved!';
            btn.classList.add('btn-saved');
            btn.disabled = true;
        }
    } catch (error) {
        console.error('Error saving recipe:', error);
        showError(error.message || 'Failed to save recipe');
    }
}

async function deleteSavedRecipe(recipeId) {
    try {
        const response = await fetch(`${API_BASE_URL}/recipes/saved/${recipeId}`, {
            method: 'DELETE',
            headers: getAuthHeaders()
        });

        if (response.status === 401) {
            handleAuthError();
            return;
        }

        if (!response.ok) throw new Error('Failed to delete recipe');

        savedRecipes = savedRecipes.filter(r => r.id !== recipeId);
        renderSavedRecipes();
    } catch (error) {
        console.error('Error deleting recipe:', error);
        showError('Failed to delete recipe');
    }
}

// ============================================
// Utility Functions
// ============================================

function setLoading(loading) {
    generateBtn.disabled = loading;
    generateBtnText.style.display = loading ? 'none' : 'inline';
    generateBtnSpinner.style.display = loading ? 'inline-block' : 'none';
}

function showError(message) {
    errorMessage.textContent = message;
    errorMessage.style.display = 'block';
    setTimeout(() => {
        errorMessage.style.display = 'none';
    }, 5000);
}

function hideError() {
    errorMessage.style.display = 'none';
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
