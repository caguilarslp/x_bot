# X.com Profile Editing XPath Selectors

## Method 1: Single Modal Profile Edit

### Profile Navigation
```xpath
// Profile Link
//a[@data-testid="AppTabBar_Profile_Link"]

// Edit Profile Button
//span[contains(text(), "Edit profile")]
```

### Profile Edit Modal Fields
```xpath
// Name Input
//input[@name="displayName"]

// Bio Textarea
//textarea[@name="description"]

// Location Input
//input[@name="location"]

// Website Input
//input[@name="url"]

// Profile Picture Upload
//input[@type="file" and contains(@accept, "image/")]

// Save Button
//button[@data-testid="Profile_Save_Button"]
```

## Method 2: Step-by-Step Profile Setup

### Initial Setup Button
```xpath
// Setup/Edit Profile Button
//span[contains(text(), "Set up Profile")]
//span[contains(text(), "Edit profile")]
```

### Stage 1: Profile Picture
```xpath
// Modal Header
//h1[contains(text(), "Pick a profile picture")]

// Photo Upload Input
//input[@data-testid="fileInput" and @type="file"]

// Skip Button
//button[@data-testid="ocfSelectAvatarSkipForNowButton"]

// Next Button
//button[@data-testid="ocfSelectAvatarNextButton"]
```

### Stage 2: Header/Banner
```xpath
// Modal Header
//h1[contains(text(), "Pick a header")]

// Banner Upload Input
//input[@data-testid="fileInput" and @type="file"]

// Skip Button
//button[@data-testid="ocfSelectBannerSkipForNowButton"]

// Next Button
//button[@data-testid="ocfSelectBannerNextButton"]
```

### Stage 3: Bio/Description
```xpath
// Modal Header
//h1[contains(text(), "Describe yourself")]

// Bio Textarea
//textarea[@data-testid="ocfEnterTextTextInput" and @name="text"]

// Skip Button
//button[@data-testid="ocfEnterTextSkipForNowButton"]

// Next Button
//button[@data-testid="ocfEnterTextNextButton"]
```

### Stage 4: Location
```xpath
// Modal Header
//h1[contains(text(), "Where do you live?")]

// Location Input
//input[@data-testid="ocfEnterTextTextInput" and @name="text"]

// Skip Button
//button[@data-testid="ocfEnterTextSkipForNowButton"]

// Next Button (not always present)
//button[@data-testid="ocfEnterTextNextButton"]
```

### Final Save Stage
```xpath
// Save Button
//button[@data-testid="OCF_CallToAction_Button"]

// Close/Cancel Button
//button[@data-testid="app-bar-close"]
```

## General Automation Strategies

### Flexible Selector Techniques
```xpath
// Text-based selection
//span[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'edit profile')]

// Partial attribute matching
//input[contains(@class, 'profile-input')]

// Hierarchical selection
//div[@role='dialog']//button[contains(@class, 'save-button')]
```

## Notes
- Selectors may change with platform updates
- Always implement fallback and error handling
- Use dynamic waiting strategies
- Simulate human-like interaction speeds