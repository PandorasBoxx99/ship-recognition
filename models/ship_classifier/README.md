---
license: apache-2.0
metrics:
- accuracy
- f1
base_model:
- google/vit-base-patch16-224-in21k
---
Returns ship type given an image with about 99.6% accuracy.

See https://www.kaggle.com/code/dima806/ship-type-detection-vit for more details.

```
Classification report:

                  precision    recall  f1-score   support

         Bulkers     0.9927    1.0000    0.9963       409
    Recreational     0.9902    0.9927    0.9915       409
        Sailboat     0.9975    0.9853    0.9914       409
             DDG     0.9976    1.0000    0.9988       409
  Container Ship     1.0000    0.9951    0.9975       409
             Tug     0.9951    0.9927    0.9939       410
Aircraft Carrier     1.0000    0.9976    0.9988       409
          Cruise     1.0000    1.0000    1.0000       409
       Submarine     0.9927    1.0000    0.9964       410
     Car Carrier     0.9951    0.9976    0.9963       409

        accuracy                         0.9961      4092
       macro avg     0.9961    0.9961    0.9961      4092
    weighted avg     0.9961    0.9961    0.9961      4092
```